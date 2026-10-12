// Auto-update from GitHub Releases (nsfxu/careerlab), installed app only.
// Downloads in the background; the window shows "restart to update" and the user decides
// when. If they never restart, the update installs when the app quits.
const { app, ipcMain } = require("electron");

let state = { status: "idle" };   // idle | disabled | checking | none | downloading | ready | error

function init(getWindow) {
  const send = (patch) => {
    state = { ...state, ...patch };
    const w = getWindow();
    if (w && !w.isDestroyed()) w.webContents.send("update", state);
  };
  ipcMain.handle("update-state", () => state);

  if (!app.isPackaged) {                     // dev runs from source: nothing to update
    state = { status: "disabled" };
    ipcMain.handle("update-check", () => state);
    ipcMain.handle("update-install", () => false);
    return;
  }

  const { autoUpdater } = require("electron-updater");
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.on("checking-for-update", () => send({ status: "checking", error: undefined }));
  autoUpdater.on("update-not-available", () => send({ status: "none" }));
  autoUpdater.on("update-available", (info) => send({ status: "downloading", version: info.version, percent: 0 }));
  autoUpdater.on("download-progress", (p) => send({ status: "downloading", percent: Math.round(p.percent) }));
  autoUpdater.on("update-downloaded", (info) => send({ status: "ready", version: info.version }));
  autoUpdater.on("error", (e) => {
    const msg = String((e && e.message) || e).split("\n")[0];
    // 404 = no published release (yet): nothing to update, not a failure
    send(/\b404\b/.test(msg) ? { status: "none" } : { status: "error", error: msg });
  });

  const check = () => autoUpdater.checkForUpdates().catch(() => {});
  ipcMain.handle("update-check", async () => { await check(); return state; });
  ipcMain.handle("update-install", () => {
    // silent install, then start CareerLab again; the engine child is stopped on window close
    setImmediate(() => autoUpdater.quitAndInstall(true, true));
    return true;
  });
  setTimeout(check, 5000);
  setInterval(check, 6 * 3600 * 1000);
}

module.exports = { init };
