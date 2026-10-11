// CareerLab main process: one window, one long-lived Python engine child.
// All save-format knowledge lives in the engine; this file only routes requests.
const { app, BrowserWindow, ipcMain, shell } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const readline = require("readline");

let engine = null;
let nextId = 1;
const pending = new Map();

function engineCommand() {
  // Packaged: the frozen engine sits in resources/engine. Dev: run the package with Python.
  const frozen = path.join(process.resourcesPath || "", "engine", "careerlab-engine.exe");
  if (app.isPackaged) return { cmd: frozen, args: [], cwd: path.dirname(frozen) };
  return { cmd: "python", args: ["-m", "fl26.rpc"], cwd: path.join(__dirname, "..", "engine") };
}

function startEngine() {
  const { cmd, args, cwd } = engineCommand();
  engine = spawn(cmd, args, { cwd, env: { ...process.env, PYTHONIOENCODING: "utf-8" }, windowsHide: true });
  readline.createInterface({ input: engine.stdout }).on("line", (line) => {
    let msg;
    try { msg = JSON.parse(line); } catch { return; }
    const p = pending.get(msg.id);
    if (!p) return;
    pending.delete(msg.id);
    msg.ok ? p.resolve(msg.result) : p.reject(new Error(msg.error));
  });
  engine.stderr.on("data", (d) => process.stderr.write(d));
  engine.on("exit", (code) => {
    for (const p of pending.values()) p.reject(new Error(`engine exited (${code})`));
    pending.clear();
    engine = null;
  });
}

function call(method, params = {}) {
  if (!engine) startEngine();
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    engine.stdin.write(JSON.stringify({ id, method, params }) + "\n");
  });
}

ipcMain.handle("engine", (_e, method, params) => call(method, params));
ipcMain.handle("reveal", (_e, file) => shell.showItemInFolder(file));

function createWindow() {
  const win = new BrowserWindow({
    width: 1400, height: 900, minWidth: 1100, minHeight: 700,
    backgroundColor: "#121212",
    title: "CareerLab",
    autoHideMenuBar: true,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, nodeIntegration: false },
  });
  win.loadFile(path.join(__dirname, "renderer", "index.html"));
}

app.whenReady().then(() => { startEngine(); createWindow(); });
app.on("window-all-closed", () => { if (engine) engine.kill(); app.quit(); });
