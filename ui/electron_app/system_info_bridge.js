// Friday AI - System Information Bridge
// This module provides integration between the Python backend and Electron frontend for system information

const { ipcMain, ipcRenderer } = require('electron');
const os = require('os');

// For main process
class SystemInfoBridge {
    constructor() {
        // Initialize counters
        this.lastCpuInfo = this._getCpuInfo();
        this.lastMeasurementTime = Date.now();
        
        // Set up IPC handlers
        this._setupHandlers();
        
        // Default update interval (ms)
        this.updateInterval = 5000;
        this.updateTimer = null;
        
        // Optional backend API URL
        this.apiUrl = null;
    }
    
    _setupHandlers() {
        // Handle requests for system info
        ipcMain.handle('get-system-info', async () => {
            return this.getSystemInfo();
        });
        
        // Handle start/stop monitoring
        ipcMain.handle('start-system-monitoring', (event, interval) => {
            return this.startMonitoring(interval);
        });
        
        ipcMain.handle('stop-system-monitoring', () => {
            return this.stopMonitoring();
        });
        
        // Handle setting backend API URL
        ipcMain.handle('set-system-info-api', (event, url) => {
            this.apiUrl = url;
            return { success: true };
        });
    }
    
    async getSystemInfo() {
        // If API URL is set, get info from backend
        if (this.apiUrl) {
            try {
                const response = await fetch(`${this.apiUrl}/system_info`);
                if (response.ok) {
                    return await response.json();
                }
            } catch (error) {
                console.error('Error fetching system info from backend:', error);
                // Fall back to local info
            }
        }
        
        // Get local system info
        return this._getLocalSystemInfo();
    }
    
    _getLocalSystemInfo() {
        // Calculate CPU usage
        const currentCpuInfo = this._getCpuInfo();
        const cpuUsage = this._calculateCpuUsage(this.lastCpuInfo, currentCpuInfo);
        this.lastCpuInfo = currentCpuInfo;
        
        // Memory info
        const totalMem = os.totalmem();
        const freeMem = os.freemem();
        const usedMem = totalMem - freeMem;
        const memoryPercent = Math.round((usedMem / totalMem) * 100);
        
        // System info
        return {
            hostname: os.hostname(),
            platform: os.platform(),
            arch: os.arch(),
            release: os.release(),
            uptime: this._formatUptime(os.uptime()),
            cpu: {
                model: os.cpus()[0].model,
                cores: os.cpus().length,
                usage: cpuUsage
            },
            memory: {
                total: this._formatBytes(totalMem),
                free: this._formatBytes(freeMem),
                used: this._formatBytes(usedMem),
                percent: memoryPercent
            },
            network: this._getNetworkInfo(),
            time: new Date().toLocaleString()
        };
    }
    
    _getCpuInfo() {
        const cpus = os.cpus();
        let user = 0, nice = 0, sys = 0, idle = 0, irq = 0;
        
        for (const cpu of cpus) {
            user += cpu.times.user;
            nice += cpu.times.nice;
            sys += cpu.times.sys;
            idle += cpu.times.idle;
            irq += cpu.times.irq;
        }
        
        return { user, nice, sys, idle, irq };
    }
    
    _calculateCpuUsage(prev, current) {
        const prevTotal = prev.user + prev.nice + prev.sys + prev.idle + prev.irq;
        const currentTotal = current.user + current.nice + current.sys + current.idle + current.irq;
        
        const totalDiff = currentTotal - prevTotal;
        const idleDiff = current.idle - prev.idle;
        
        return Math.round(100 * (1 - idleDiff / totalDiff));
    }
    
    _getNetworkInfo() {
        const interfaces = os.networkInterfaces();
        const networkInfo = [];
        
        for (const [name, interfaceInfo] of Object.entries(interfaces)) {
            for (const info of interfaceInfo) {
                if (info.family === 'IPv4') {
                    networkInfo.push({
                        name,
                        address: info.address,
                        netmask: info.netmask,
                        mac: info.mac
                    });
                }
            }
        }
        
        return networkInfo;
    }
    
    _formatBytes(bytes) {
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let size = bytes;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(2)} ${units[unitIndex]}`;
    }
    
    _formatUptime(seconds) {
        const days = Math.floor(seconds / (3600 * 24));
        const hours = Math.floor((seconds % (3600 * 24)) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }
    
    startMonitoring(interval) {
        // Stop existing timer if any
        this.stopMonitoring();
        
        // Set update interval
        this.updateInterval = interval || 5000;
        
        // Start timer
        this.updateTimer = setInterval(() => {
            this.getSystemInfo().then(info => {
                // Send to all renderer processes
                if (info) {
                    for (const window of require('electron').BrowserWindow.getAllWindows()) {
                        window.webContents.send('system-info-update', info);
                    }
                }
            });
        }, this.updateInterval);
        
        return { success: true, interval: this.updateInterval };
    }
    
    stopMonitoring() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
            return { success: true };
        }
        return { success: false, error: 'Monitoring not active' };
    }
}

// For renderer process
class SystemInfoRenderer {
    constructor() {
        this.onUpdate = null;
        this.isMonitoring = false;
        
        // Set up IPC handlers
        this._setupHandlers();
    }
    
    _setupHandlers() {
        // Handle system info updates from main process
        ipcRenderer.on('system-info-update', (event, info) => {
            if (this.onUpdate) {
                this.onUpdate(info);
            }
        });
    }
    
    async getSystemInfo() {
        return await ipcRenderer.invoke('get-system-info');
    }
    
    async startMonitoring(interval = 5000, callback) {
        if (callback) {
            this.onUpdate = callback;
        }
        
        const result = await ipcRenderer.invoke('start-system-monitoring', interval);
        this.isMonitoring = result.success;
        return result;
    }
    
    async stopMonitoring() {
        const result = await ipcRenderer.invoke('stop-system-monitoring');
        this.isMonitoring = false;
        return result;
    }
    
    async setApiUrl(url) {
        return await ipcRenderer.invoke('set-system-info-api', url);
    }
}

// Export the appropriate class depending on process type
if (process.type === 'renderer') {
    module.exports = new SystemInfoRenderer();
} else {
    module.exports = SystemInfoBridge;
}