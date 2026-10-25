@echo off
setlocal enabledelayedexpansion
title SparkAssistant Universal Appliance
color 0b

:: 1. Dynamic path detection
set "PEN_DIR=%~dp0"
if "%PEN_DIR:~-1%"=="\" set "PEN_DIR=%PEN_DIR:~0,-1%"

:: 2. Isolate paths to pen drive
set "PATH=%PEN_DIR%\bin\python;%PEN_DIR%\bin\python\Scripts;%PEN_DIR%\bin\ollama;%PEN_DIR%\kiwix;%PATH%"
set "OLLAMA_MODELS=%PEN_DIR%\models"
set "OLLAMA_KEEP_ALIVE=-1"
set "OLLAMA_NUM_THREADS=4"

:: 3. Scan for HDD Database
set "HDD_XML="
set "HDD_DRIVE="

for %%D in (D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist "%%D:\SparkVault\kiwix\library.xml" (
        set "HDD_XML=%%D:\SparkVault\kiwix\library.xml"
        set "HDD_DRIVE=%%D:"
    ) else if exist "%%D:\SparkVault_Data\library.xml" (
        set "HDD_XML=%%D:\SparkVault_Data\library.xml"
        set "HDD_DRIVE=%%D:"
    )
)

:: 4. Start Kiwix if HDD is found
if defined HDD_XML (
    echo [OK] 136GB Vault HDD Detected on !HDD_DRIVE!
    netstat -ano | findstr :8088 >nul
    if !errorlevel! neq 0 (
        echo [1/2] Starting Kiwix Server...
        start "" /min "%PEN_DIR%\kiwix\kiwix-serve.exe" --port=8088 --library "!HDD_XML!"
        timeout /t 2 /nobreak >nul
    ) else (
        echo [1/2] Kiwix Server active on :8088.
    )
) else (
    echo [INFO] HDD not detected. Operating in Lite Mode (Web + 3B Neural).
)

:: 5. Start Portable Ollama Engine
netstat -ano | findstr :11434 >nul
if !errorlevel! neq 0 (
    echo [2/2] Starting Portable Ollama Engine...
    start "" /min "%PEN_DIR%\bin\ollama\ollama.exe" serve
    timeout /t 3 /nobreak >nul
) else (
    echo [2/2] Ollama Engine active on :11434.
)

:: 6. Launch the Compiled SparkAssistant Application
echo [3/3] Launching SparkAssistant...
cd /d "%PEN_DIR%"

if exist "%PEN_DIR%\SparkAssistant.exe" (
    "%PEN_DIR%\SparkAssistant.exe"
) else (
    "%PEN_DIR%\bin\python\python.exe" "%PEN_DIR%\main.py"
)

echo.
echo [SparkAssistant] Session ended.
pause
