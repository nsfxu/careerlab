const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("cl", {
  call: (method, params) => ipcRenderer.invoke("engine", method, params),
  reveal: (file) => ipcRenderer.invoke("reveal", file),
  pickFolder: (title) => ipcRenderer.invoke("pick-folder", title),
  pickSave: (title, name) => ipcRenderer.invoke("pick-save", title, name),
  version: () => ipcRenderer.invoke("version"),
  updateState: () => ipcRenderer.invoke("update-state"),
  checkUpdates: () => ipcRenderer.invoke("update-check"),
  installUpdate: () => ipcRenderer.invoke("update-install"),
  onUpdate: (cb) => ipcRenderer.on("update", (_e, st) => cb(st)),
});
