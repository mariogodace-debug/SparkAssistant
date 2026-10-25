@echo off
setlocal enabledelayedexpansion
title SparkVault Portable Hybrid Intelligence
color 0b

:: Auto-detect current drive and directory
set "VAULT_DIR=%~dp0"
if "%VAULT_DIR:~-1%"=="\" set "VAULT_DIR=%VAULT_DIR:~0,-1%"

echo [SparkVault] Mounted on: %VAULT_DIR%

:: Session-only variables (does not touch host PC registry)
set "OLLAMA_MODELS=%VAULT_DIR%\models"
set "OLLAMA_KEEP_ALIVE=-1"
set "OLLAMA_NUM_THREADS=4"
set "PATH=%VAULT_DIR%\kiwix;%PATH%"

:: Check / Start Kiwix Server on port 8088
netstat -ano | findstr :8088 >nul
if %errorlevel% neq 0 (
    echo [1/3] Starting Portable Kiwix Server...
    start "" /min "%VAULT_DIR%\kiwix\kiwix-serve.exe" --port=8088 --library "%VAULT_DIR%\kiwix\library.xml"
    timeout /t 2 /nobreak >nul
) else (
    echo [1/3] Kiwix Server active on port 8088.
)

:: Check / Start Ollama engine
netstat -ano | findstr :11434 >nul
if %errorlevel% neq 0 (
    echo [2/3] Starting Ollama Engine from Vault...
    start "" /min ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo [2/3] Ollama Engine active.
)

:: Launch the Hybrid Assistant
echo [3/3] Starting SparkVault Assistant...
python "%VAULT_DIR%\main.py"

pause
