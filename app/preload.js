const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("cl", {
  call: (method, params) => ipcRenderer.invoke("engine", method, params),
  reveal: (file) => ipcRenderer.invoke("reveal", file),
});
