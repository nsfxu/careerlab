# Build and release

## Installer

```
python build.py
```

1. runs the engine tests;
2. freezes the engine with PyInstaller → `build/dist/careerlab-engine/` (onedir, **console**:
   the engine talks over stdio, and a windowed build has no stdin/stdout);
   `fl26/assets/DBDump.lua` is bundled as data;
3. packages the app with electron-builder (config in `app/package.json` → `build`) →
   `dist/CareerLab-Setup-<version>.exe`: NSIS, per-user, no admin, desktop + Start-menu
   shortcuts, unsigned.

The version is `app/package.json` → `version`. `main.js` picks the frozen engine when
`app.isPackaged`.

### Known build issues

- *Cannot create symbolic link* while extracting `winCodeSign`: the archive contains macOS
  symlinks, and Windows needs admin/developer mode for them. Extract it once by hand into
  `%LOCALAPPDATA%\electron-builder\Cache\winCodeSign\winCodeSign-2.6.0` (7za from
  `app/node_modules/7zip-bin`), then delete the numbered partial folders. Done on the dev PC.
- A build can fail on a locked `dist\win-unpacked` if a packaged CareerLab is still running.
- SmartScreen warns on first run (unsigned): "More info → Run anyway".

## Runtime configuration

`%LOCALAPPDATA%\CareerLab\config.json` (`gameDir`, `saveDir`), auto-detected when missing
(drive roots, `FL2026`, `Games\FL2026`, …). The Settings dialog edits it.

## Releases (`.github/workflows/release.yml`)

- `git tag v0.3.0 && git push origin v0.3.0` → Actions builds on `windows-latest` (Python 3.12,
  Node 20, `python build.py`), sets the app version from the tag, and publishes a Release
  "CareerLab 0.3.0" with the installer, `latest.yml` and the blockmap.
- *Actions → release → Run workflow* builds without publishing (installer as a run artifact).
  Verified 2026-10-12: green on a clean runner.
- Screenshots for the README: `python harness/readme_shots.py` with the app running on CDP 9333.

## Auto-update (`app/updater.js`)

- `electron-updater` (GitHub provider, `app/package.json` → `build.publish`), installed app
  only. Checks 5 s after start and every 6 h, downloads in the background, then the top bar
  shows *Restart to update* (silent install + relaunch). Unapplied staged edits trigger a
  confirm. If the user never restarts, the update installs on quit.
- It reads `latest.yml` from the newest **non-draft, non-prerelease** release of
  `nsfxu/careerlab`; the workflow uploads it with the installer and blockmap.
- Unsigned builds update fine (no publisher check without a certificate).
- Test an update: build an older version locally (`npm version 0.9.9 --no-git-tag-version`
  in `app/`, `npx electron-builder --dir`), run `dist\win-unpacked\CareerLab.exe`, and watch
  Settings → update status.

## Release checklist

1. Add the version's section to `CHANGELOG.md` (the workflow uses it as release notes).
2. Tests green; `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. Watch the run; check the Release has the `.exe`, `latest.yml` and `.blockmap`.
