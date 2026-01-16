const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("combineApi", {
  selectVault: () => ipcRenderer.invoke("select-vault"),
  listFolders: (vaultPath) => ipcRenderer.invoke("list-folders", vaultPath),
  runCombine: (payload) => ipcRenderer.invoke("run-combine", payload),
});
