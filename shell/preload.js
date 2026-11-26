// K.OS Home shell: the only thing the intro screen may tell the shell is
// "the intro video is finished".
'use strict';
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('kos', {
  introDone: () => ipcRenderer.send('kos-intro-done'),
});
