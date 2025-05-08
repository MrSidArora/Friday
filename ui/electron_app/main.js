const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const fetch = require('node-fetch'); // You may need to install this: npm install node-fetch
const SystemInfoBridge = require('./system_info_bridge');
const systemInfoBridge = new SystemInfoBridge();

// Keep a global reference of the window object to prevent garbage collection
let mainWindow;
let commandDeckWindow = null;
let pythonProcess = null;
let isOnline = false;

// Configuration
const appConfig = {
  devMode: process.argv.includes('--dev'),
  windowWidth: 1000,
  windowHeight: 700,
  minWidth: 800,
  minHeight: 600,
  pythonPath: process.env.FRIDAY_PYTHON_PATH || 'python', // Path to Python executable
  uiControllerScript: path.join(__dirname, '..', 'ui_controller.py'),
  // Using the HTTP port now instead of WebSocket with explicit IPv4 address
  httpServerUrl: 'http://127.0.0.1:5000'
};

// IPC Handlers
ipcMain.handle('get-online-status', async () => {
  try {
    // Try to get status from the HTTP server
    const response = await fetch(`${appConfig.httpServerUrl}/status`);
    const data = await response.json();
    isOnline = data.online;
    return isOnline;
  } catch (error) {
    console.error('Error getting online status:', error);
    return false;
  }
});

ipcMain.handle('toggle-online-status', async () => {
  try {
    isOnline = !isOnline;
    
    // Send status to Python backend
    const response = await fetch(`${appConfig.httpServerUrl}/set_online_status`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ online: isOnline }),
    });
    
    const result = await response.json();
    return { success: true, online: isOnline, result };
  } catch (error) {
    console.error('Error setting online status:', error);
    return { success: false, error: error.message };
  }
});

// New IPC handler for opening Command Deck
ipcMain.handle('open-command-deck', async () => {
  try {
    // Check if Command Deck is available
    const response = await fetch(`${appConfig.httpServerUrl}/status`);
    const data = await response.json();
    
    if (data.command_deck_available) {
      if (commandDeckWindow) {
        // If window exists, just focus it
        if (commandDeckWindow.isMinimized()) commandDeckWindow.restore();
        commandDeckWindow.focus();
        return { success: true };
      } else {
        // Create a new window for Command Deck
        createCommandDeckWindow();
        return { success: true };
      }
    } else {
      return { success: false, error: 'Command Deck is not available' };
    }
  } catch (error) {
    console.error('Error opening Command Deck:', error);
    return { success: false, error: error.message };
  }
});

// Function to check HTTP server
function checkHttpServer(url, maxAttempts = 5, delayBetweenAttempts = 1000) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    
    function attemptConnection() {
      attempts++;
      console.log(`Attempting to connect to HTTP server (${attempts}/${maxAttempts})...`);
      
      fetch(`${url}/status`)
        .then(response => {
          if (response.ok) {
            console.log('Successfully connected to HTTP server');
            resolve(true);
          } else {
            throw new Error(`HTTP server returned status: ${response.status}`);
          }
        })
        .catch(error => {
          console.log(`HTTP connection attempt failed: ${error.message}`);
          
          if (attempts < maxAttempts) {
            setTimeout(attemptConnection, delayBetweenAttempts);
          } else {
            console.error(`Failed to connect to HTTP server after ${maxAttempts} attempts`);
            reject(new Error('HTTP server not available'));
          }
        });
    }
    
    attemptConnection();
  });
}

function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: appConfig.windowWidth,
    height: appConfig.windowHeight,
    minWidth: appConfig.minWidth,
    minHeight: appConfig.minHeight,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    },
    // Use a clean, modern style for the window
    backgroundColor: '#ffffff',
    // Remove default menu for cleaner look
    autoHideMenuBar: !appConfig.devMode
  });

  // Load the index.html file
  mainWindow.loadFile('index.html');
  
  // Open DevTools in development mode
  if (appConfig.devMode) {
    mainWindow.webContents.openDevTools();
  }

  // Window event handlers
  mainWindow.on('closed', () => {
    mainWindow = null;
    stopPythonController();
    
    // Close Command Deck window if open
    if (commandDeckWindow) {
      commandDeckWindow.close();
      commandDeckWindow = null;
    }
  });

  systemInfoBridge.startMonitoring(5000);
}

// Create the Command Deck window
function createCommandDeckWindow() {
  if (commandDeckWindow) {
    commandDeckWindow.focus();
    return;
  }
  
  commandDeckWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    title: 'Friday AI - Command Deck',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    },
    backgroundColor: '#121212', // Dark background
    autoHideMenuBar: !appConfig.devMode
  });
  
  // Load the Command Deck URL
  commandDeckWindow.loadURL(`${appConfig.httpServerUrl}/dashboard`);
  
  // Open DevTools in development mode
  if (appConfig.devMode) {
    commandDeckWindow.webContents.openDevTools();
  }
  
  commandDeckWindow.on('closed', () => {
    commandDeckWindow = null;
  });
}

// Start the Python UI controller
function startPythonController() {
  // Check if the UI controller script exists
  if (!fs.existsSync(appConfig.uiControllerScript)) {
    console.error(`UI controller script not found: ${appConfig.uiControllerScript}`);
    return false;
  }

  // Launch the Python process
  const devModeFlag = appConfig.devMode ? "--dev-mode" : "";
  pythonProcess = spawn(appConfig.pythonPath, [appConfig.uiControllerScript, devModeFlag]);

  console.log('Python UI controller started');

  // Log stdout and stderr
  pythonProcess.stdout.on('data', (data) => {
    console.log(`Python stdout: ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python stderr: ${data}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);
    pythonProcess = null;
  });

  return true;
}

// Stop the Python UI controller
function stopPythonController() {
  if (pythonProcess) {
    console.log('Stopping Python UI controller');
    pythonProcess.kill();
    pythonProcess = null;
  }
}

// Create window when Electron has finished initialization
app.whenReady().then(async () => {
  // Add this line here to set a custom userData path
  app.setPath('userData', path.join(app.getPath('appData'), 'friday-ai-electron'));

  // Note: We're not starting Python UI controller here anymore
  // Instead, we assume the main.py process is already running
  
  try {
    // Check if HTTP server is available (the main Friday system)
    await checkHttpServer(appConfig.httpServerUrl);
    console.log('HTTP server is available, connection confirmed');
  } catch (error) {
    console.warn('HTTP server check failed:', error.message);
    console.log('Make sure the Friday system is running (python main.py)');
  }

  createWindow();

  // On macOS, re-create window when dock icon is clicked
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopPythonController();
    app.quit();
  }
});

// Clean up on exit
app.on('before-quit', () => {
  stopPythonController();
});