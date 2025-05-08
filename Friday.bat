@echo off
setlocal enabledelayedexpansion

REM Friday AI System Launcher
REM Final Version

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Log startup
echo %date% %time% - Starting Friday AI system... >> logs\friday_startup.log

REM Process command line arguments
set START_COMMAND_DECK=0
set LAUNCH_MODE=--server

:PARSE_ARGS
if "%~1"=="" goto ARGS_DONE
if /i "%~1"=="--command-deck" set START_COMMAND_DECK=1
if /i "%~1"=="--interactive" set LAUNCH_MODE=--interactive
shift
goto PARSE_ARGS
:ARGS_DONE

REM Check if process is already running
tasklist /FI "WINDOWTITLE eq Friday Backend" 2>NUL | find "cmd.exe" >NUL
if %ERRORLEVEL% EQU 0 (
    echo Friday is already running!
    echo If this is an error, close the existing Friday windows first.
    echo %date% %time% - Launch failed: Friday already running >> logs\friday_startup.log
    pause
    exit /b 1
) else (
    if exist friday.lock (
        echo Stale lock file found, removing...
        del friday.lock
        echo %date% %time% - Removed stale lock file >> logs\friday_startup.log
    )
)

REM Create a lockfile to prevent multiple instances
echo %date% %time% > friday.lock

REM Start the main Python backend and keep it running
echo Starting Friday AI system...
echo %date% %time% - Launching Python backend >> logs\friday_startup.log

if %START_COMMAND_DECK%==1 (
    start "Friday Backend" cmd /c "python main.py %LAUNCH_MODE% --command-deck && del friday.lock"
    echo Command Deck mode enabled
    echo %date% %time% - Command Deck mode enabled >> logs\friday_startup.log
) else (
    start "Friday Backend" cmd /c "python main.py %LAUNCH_MODE% && del friday.lock"
)

REM Wait for the backend to initialize
echo Waiting for backend to start...
timeout /t 3 /nobreak > nul

REM Test HTTP connection with retries
echo Testing connection to backend...
set MAX_RETRIES=6
set RETRY_COUNT=0

:CONNECTION_RETRY
python -c "import requests; exit(0 if requests.get('http://localhost:5000/status').status_code == 200 else 1)" 2>nul
if %ERRORLEVEL% EQU 0 goto CONNECTION_SUCCESS
set /a RETRY_COUNT+=1
if %RETRY_COUNT% LSS %MAX_RETRIES% (
    echo Retry %RETRY_COUNT%/%MAX_RETRIES%...
    timeout /t 2 /nobreak > nul
    goto CONNECTION_RETRY
)
echo Failed to connect to backend after %MAX_RETRIES% attempts!
echo Check if main.py is running correctly.
echo %date% %time% - Connection test failed after %MAX_RETRIES% attempts >> logs\friday_startup.log
del friday.lock
pause
exit /b 1

:CONNECTION_SUCCESS
echo Connection successful!
echo %date% %time% - Backend connection successful >> logs\friday_startup.log

REM Start the Electron UI
echo Starting Electron UI...
cd ui\electron_app
start "Friday UI" cmd /c "npm start"
cd ..\..
echo %date% %time% - Electron UI started >> logs\friday_startup.log

echo Friday system started successfully!
echo.
echo Press any key to shut down Friday (closes all components)...
pause > nul

REM Shutdown the system
echo Shutting down Friday system...
echo %date% %time% - Beginning system shutdown >> logs\friday_startup.log
taskkill /FI "WINDOWTITLE eq Friday Backend" /T /F > nul 2>&1
taskkill /FI "WINDOWTITLE eq Friday UI" /T /F > nul 2>&1
del friday.lock
echo %date% %time% - Friday system shut down successfully >> logs\friday_startup.log

echo Friday system shut down.
pause