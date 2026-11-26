// K.OS Home shell: the small set of things pages may ask the shell to do.
//   introDone()           the startup video is finished (intro screen)
//   menu(action, arg)     Quick Menu: close, resume, home, keys (for example 'KEY_LEFTSHIFT+KEY_TAB')
//   onMenu(callback)      Quick Menu: called with 'show' or 'hide'
'use strict';
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('kos', {
  introDone: () => ipcRenderer.send('kos-intro-done'),
  menu: (action, arg) => ipcRenderer.send('kos-menu', String(action), arg === undefined ? '' : String(arg)),
  onMenu: (cb) => {
    ipcRenderer.on('kos-menu-show', () => cb('show'));
    ipcRenderer.on('kos-menu-hide', () => cb('hide'));
  },
});
