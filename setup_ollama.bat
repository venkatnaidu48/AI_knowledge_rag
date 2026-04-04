@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM AUTOMATED OLLAMA SETUP FOR WINDOWS
REM ============================================================================

title Ollama Setup - RAG System

echo.
echo ============================================================================
echo SETTING UP OLLAMA FOR RAG SYSTEM
echo ============================================================================
echo.

REM Check if Ollama is installed
echo Step 1: Checking Ollama installation...
where ollama >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo   [OK] Ollama is installed
    for /f "tokens=*" %%i in ('ollama --version') do (
        echo   Version: %%i
    )
) else (
    echo   [ERROR] Ollama not found
    echo.
    echo   Please install Ollama:
    echo   1. Download: https://ollama.ai/download (Windows)
    echo   2. Run OllamaSetup.exe
    echo   3. Restart your computer
    echo   4. Run this script again
    echo.
    pause
    exit /b 1
)

REM Check if Ollama is running
echo.
echo Step 2: Checking if Ollama server is running...

curl -s http://localhost:11434/api/tags >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo   [OK] Ollama server is running on localhost:11434
) else (
    echo   [WARN] Ollama server not responding
    echo.
    echo   Starting Ollama server...
    echo   A new window will open - keep it running in background
    echo.
    start cmd /k "ollama serve"
    timeout /t 3 /nobreak
    
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo   [OK] Ollama server started successfully
    ) else (
        echo   [ERROR] Could not start Ollama server
        echo.
        echo   Try starting manually:
        echo   1. Open Command Prompt
        echo   2. Run: ollama serve
        pause
        exit /b 1
    )
)

REM Check for mistral model
echo.
echo Step 3: Checking for Mistral model...

for /f "delims=" %%i in ('ollama list 2^>nul ^| findstr /R "mistral"') do (
    set "MISTRAL_CHECK=%%i"
)

if defined MISTRAL_CHECK (
    echo   [OK] Mistral model found
    echo   %MISTRAL_CHECK%
) else (
    echo   [WARN] Mistral model not installed
    echo.
    echo   Downloading Mistral model (~4GB)...
    echo   This takes 2-3 minutes depending on speed...
    echo.
    
    ollama pull mistral
    
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo   [OK] Mistral model downloaded successfully
    ) else (
        echo.
        echo   [ERROR] Failed to download Mistral model
        echo.
        echo   Try manually:
        echo   1. Open Command Prompt
        echo   2. Run: ollama pull mistral
        pause
        exit /b 1
    )
)

REM Summary
echo.
echo ============================================================================
echo OLLAMA SETUP COMPLETE!
echo ============================================================================
echo.
echo Active Models:
ollama list
echo.
echo Status:
echo   [OK] Ollama installed and running
echo   [OK] Mistral model available
echo.
echo Next Steps:
echo   1. Keep Ollama running in the background
echo   2. Run: python test_all_providers.py
echo   3. Run: python src/rag_pipeline_improved.py (to test RAG)
echo.
echo Notes:
echo   - Ollama runs on http://localhost:11434
echo   - Mistral model will be used as fallback (if OpenAI/Groq unavailable)
echo   - Restart this script if model list is empty
echo.
pause
