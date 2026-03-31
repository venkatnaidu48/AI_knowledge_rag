@echo off
REM Automated Test Runner for RAG Application (Windows)
REM Runs all test suites and generates reports

setlocal enabledelayedexpansion

REM Configuration
set PYTHON_CMD=python
set TEST_DIR=tests
set REPORTS_DIR=test-reports
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set TIMESTAMP=!mydate!_!mytime!

echo.
echo ==========================================
echo RAG Application - Automated Test Runner
echo ==========================================
echo.

REM Create reports directory
if not exist "%REPORTS_DIR%" mkdir "%REPORTS_DIR%"

REM Check if pytest is installed
%PYTHON_CMD% -m pytest --version > nul 2>&1
if errorlevel 1 (
    echo Installing test dependencies...
    %PYTHON_CMD% -m pip install pytest pytest-cov pytest-asyncio pytest-html pytest-xdist pytest-timeout
)

REM UNIT TESTS
echo [1/4] Running Unit Tests...
%PYTHON_CMD% -m pytest "%TEST_DIR%\unit" ^
    -v ^
    --cov=src ^
    --cov-report=html:"%REPORTS_DIR%\coverage_unit_%TIMESTAMP%" ^
    --html="%REPORTS_DIR%\unit_tests_%TIMESTAMP%.html" ^
    --self-contained-html ^
    -m "unit" > "%REPORTS_DIR%\unit_tests_%TIMESTAMP%.log" 2>&1

echo SUCCESS: Unit tests complete
echo.

REM INTEGRATION TESTS
echo [2/4] Running Integration Tests...
%PYTHON_CMD% -m pytest "%TEST_DIR%\integration" ^
    -v ^
    --cov=src ^
    --cov-report=html:"%REPORTS_DIR%\coverage_integration_%TIMESTAMP%" ^
    --html="%REPORTS_DIR%\integration_tests_%TIMESTAMP%.html" ^
    --self-contained-html ^
    -m "integration" ^
    --timeout=60 > "%REPORTS_DIR%\integration_tests_%TIMESTAMP%.log" 2>&1

echo SUCCESS: Integration tests complete
echo.

REM PERFORMANCE TESTS
echo [3/4] Running Performance Tests...
%PYTHON_CMD% -m pytest "%TEST_DIR%\performance" ^
    -v ^
    --benchmark-only ^
    --html="%REPORTS_DIR%\performance_tests_%TIMESTAMP%.html" ^
    --self-contained-html ^
    -m "performance" > "%REPORTS_DIR%\performance_tests_%TIMESTAMP%.log" 2>&1

echo SUCCESS: Performance tests complete
echo.

REM COVERAGE SUMMARY
echo [4/4] Generating Coverage Report...
%PYTHON_CMD% -m pytest "%TEST_DIR%" ^
    -v ^
    --cov=src ^
    --cov-report=term-missing ^
    --cov-report=html:"%REPORTS_DIR%\coverage_combined_%TIMESTAMP%" ^
    --cov-report=xml:"%REPORTS_DIR%\coverage_%TIMESTAMP%.xml" ^
    --html="%REPORTS_DIR%\all_tests_%TIMESTAMP%.html" ^
    --self-contained-html ^
    --tb=short > "%REPORTS_DIR%\all_tests_%TIMESTAMP%.log" 2>&1

echo SUCCESS: Coverage report complete
echo.

echo ==========================================
echo Test Summary Report
echo ==========================================
echo.

echo Report Artifacts:
echo   Unit Tests:              %REPORTS_DIR%\unit_tests_%TIMESTAMP%.html
echo   Integration Tests:       %REPORTS_DIR%\integration_tests_%TIMESTAMP%.html
echo   Performance Tests:       %REPORTS_DIR%\performance_tests_%TIMESTAMP%.html
echo   Coverage Report:         %REPORTS_DIR%\coverage_combined_%TIMESTAMP%\index.html
echo   Combined Report:         %REPORTS_DIR%\all_tests_%TIMESTAMP%.html
echo   XML Report:              %REPORTS_DIR%\coverage_%TIMESTAMP%.xml
echo.

echo Report Directory Contents:
dir /s "%REPORTS_DIR%"

echo.
echo Opening test reports in browser...
if exist "%REPORTS_DIR%\all_tests_%TIMESTAMP%.html" (
    start "" "%REPORTS_DIR%\all_tests_%TIMESTAMP%.html"
)

pause
