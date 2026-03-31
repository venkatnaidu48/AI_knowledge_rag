@echo off
REM Fast Q&A startup script - Optimized for speed

cls
echo ========================================
echo FAST Q&A - OPTIMIZED FOR SPEED
echo ========================================
echo.
echo This version is optimized for 3-15 second responses
echo (vs 10-60 seconds in advanced_qa.py)
echo.
echo Starting...
echo.

.venv\Scripts\python.exe fast_qa.py

pause
