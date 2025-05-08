@echo off
REM Friday AI Setup Script (Ollama version)
echo Setting up Friday AI development environment with existing Ollama...

REM Ensure Ollama is installed
where ollama >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Ollama is not installed. Please install it from https://ollama.com and try again.
    exit /b 1
)

REM Check if Ollama is running
curl -s http://localhost:11434/api/version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Ollama doesn't seem to be running. Please start Ollama before continuing.
    set /p CONTINUE=Continue anyway? (y/n) 
    if /I NOT "%CONTINUE%"=="y" exit /b 1
)

echo Verifying model installation...
ollama list | findstr "mixtral" >nul
IF %ERRORLEVEL% NEQ 0 (
    echo Mixtral model not found. Pulling mixtral:latest...
    ollama pull mixtral:latest
)

REM Create required directories
if not exist models mkdir models
if not exist logs mkdir logs
if not exist data mkdir data
if not exist config mkdir config


echo Friday AI environment setup complete!
