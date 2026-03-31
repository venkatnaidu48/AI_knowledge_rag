@echo off
REM RAG Application Startup Script for Windows

echo.
echo =========================================
echo RAG Application - Startup Script
echo =========================================
echo.

REM 1. Check Python version
echo [1/5] Checking Python version...
python --version

REM 2. Create virtual environment if not exists
if not exist "venv" (
    echo [2/5] Creating virtual environment...
    python -m venv venv
) else (
    echo [2/5] Virtual environment exists
)

REM 3. Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat

REM 4. Install dependencies
echo [4/5] Installing dependencies...
pip install -r requirements.txt

REM 5. Create necessary directories
echo [5/5] Creating data directories...
if not exist "data\uploads" mkdir data\uploads
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups
if not exist "monitoring" mkdir monitoring

echo.
echo Setup complete!
echo.
echo To start the development server:
echo   python -m uvicorn src.main:app --reload
echo.
echo To access the API:
echo   http://localhost:8000/docs
echo.
pause
