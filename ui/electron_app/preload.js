// preload.js
const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing all of electron
contextBridge.exposeInMainWorld(
  'electronAPI', {
    // Online status operations
    getOnlineStatus: () => ipcRenderer.invoke('get-online-status'),
    toggleOnlineStatus: () => ipcRenderer.invoke('toggle-online-status'),
    
    // Send messages to main process
    sendMessage: (message) => ipcRenderer.send('send-to-friday', message),
    
    // Listen for responses from main process
    onResponse: (callback) => {
      ipcRenderer.on('friday-response', (event, data) => callback(data));
      return () => {
        ipcRenderer.removeAllListeners('friday-response');
      };
    },
    
    // Listen for errors
    onError: (callback) => {
      ipcRenderer.on('friday-error', (event, data) => callback(data));
      return () => {
        ipcRenderer.removeAllListeners('friday-error');
      };
    },
    
    // Listen for status updates
    onStatusUpdate: (callback) => {
      ipcRenderer.on('friday-status-update', (event, data) => callback(data));
      return () => {
        ipcRenderer.removeAllListeners('friday-status-update');
      };
    },
  // Command_Deck_function
  openCommandDeck: () => ipcRenderer.invoke('open-command-deck')

  }
);