@echo off
title SparkVault Offline Intelligence
color 0b

echo ========================================================
echo  Checking SparkVault Services...
echo ========================================================

:: 1. Check if Kiwix is running on port 8088; if not, launch it
netstat -ano | findstr :8088 >nul
if %errorlevel% neq 0 (
    echo Starting Kiwix Database Server...
    start /min "" "E:\SparkVault\kiwix\kiwix-serve.exe" --port=8088 --library "E:\SparkVault\kiwix\library.xml"
    timeout /t 2 /nobreak >nul
) else (
    echo [OK] Kiwix Database Server is active.
)

:: 2. Ensure Ollama service is active
netstat -ano | findstr :11434 >nul
if %errorlevel% neq 0 (
    echo Starting Ollama Engine...
    set OLLAMA_MODELS=E:\SparkVault\models
    start /min "" ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo [OK] Ollama Engine is active.
)

:: 3. Launch the Assistant Interface
echo [OK] Starting SparkVault Assistant...
cls
python "E:\SparkVault\fast_assistant.py"
pause
