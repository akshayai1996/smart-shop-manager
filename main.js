const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let flaskProcess;

const PYTHON_EXE = path.join(process.resourcesPath, 'extraResources', 'ShopEase.exe');
// During dev, point to built exe
const DEV_EXE_PATH = path.join(__dirname, 'build', 'exe.win-amd64-3.14', 'ShopEase.exe');

const getPort = () => {
    return new Promise((resolve, reject) => {
        // Simple check, in production you might random port or configure dynamic port
        resolve(5000); 
    });
};

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        },
        autoHideMenuBar: true
    });
    
    mainWindow.loadURL('http://127.0.0.1:5000');

    mainWindow.on('closed', function () {
        mainWindow = null;
        app.quit();
    });
}

function checkServer() {
    http.get('http://127.0.0.1:5000', (res) => {
        if (res.statusCode === 200 || res.statusCode === 302) {
            createWindow();
        } else {
            setTimeout(checkServer, 1000);
        }
    }).on('error', (err) => {
        setTimeout(checkServer, 1000);
    });
}

function startFlask() {
    let exePath = PYTHON_EXE;
    
    if (!app.isPackaged) {
        exePath = DEV_EXE_PATH;
    }

    console.log(`Starting backend from: ${exePath}`);
    
    // Check if file exists
    const fs = require('fs');
    if (!fs.existsSync(exePath)) {
        console.error(`Backend executable not found at: ${exePath}`);
        // Fallback for direct node run if exe not built yet or misplaced
        return; 
    }

    flaskProcess = spawn(exePath, [], {
        cwd: path.dirname(exePath) // Run in its own directory so it finds templates/static
    });

    flaskProcess.stdout.on('data', (data) => {
        console.log(`Flask stdout: ${data}`);
    });

    flaskProcess.stderr.on('data', (data) => {
        console.error(`Flask stderr: ${data}`);
    });
}

app.on('ready', () => {
    startFlask();
    checkServer();
});

app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') app.quit();
});

app.on('quit', () => {
    if (flaskProcess) {
        flaskProcess.kill();
    }
});
