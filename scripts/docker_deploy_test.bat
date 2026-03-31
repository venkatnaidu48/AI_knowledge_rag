@echo off
REM Docker deployment and testing script for RAG Application (Windows)
REM Usage: docker_deploy_test.bat

setlocal enabledelayedexpansion

REM Configuration
set APP_NAME=ragapp
set DOCKERFILE_PATH=Dockerfile
set DOCKER_COMPOSE_FILE=docker-compose.yml

echo.
echo ==========================================
echo RAG Application - Docker Deployment
echo ==========================================
echo.

REM PHASE 1: BUILD DOCKER IMAGE
echo [PHASE 1] Building Docker image...

if not exist "%DOCKERFILE_PATH%" (
    echo ERROR: Dockerfile not found at %DOCKERFILE_PATH%
    exit /b 1
)

docker build -t %APP_NAME%:latest -f "%DOCKERFILE_PATH%" . || (
    echo ERROR: Docker build failed
    exit /b 1
)

echo.
echo SUCCESS: Docker image built: %APP_NAME%:latest
echo.

REM PHASE 2: VALIDATE DOCKER COMPOSE
echo [PHASE 2] Validating docker-compose configuration...

if not exist "%DOCKER_COMPOSE_FILE%" (
    echo ERROR: docker-compose.yml not found
    exit /b 1
)

docker-compose -f "%DOCKER_COMPOSE_FILE%" config > nul || (
    echo ERROR: docker-compose.yml validation failed
    exit /b 1
)

echo.
echo SUCCESS: docker-compose.yml is valid
echo.

REM PHASE 3: STOP AND REMOVE EXISTING CONTAINERS
echo [PHASE 3] Cleaning up existing containers...

docker-compose -f "%DOCKER_COMPOSE_FILE%" down --remove-orphans 2>nul

echo.
echo SUCCESS: Cleanup complete
echo.

REM PHASE 4: START DOCKER COMPOSE STACK
echo [PHASE 4] Starting Docker Compose stack...

docker-compose -f "%DOCKER_COMPOSE_FILE%" up -d || (
    echo ERROR: Docker Compose startup failed
    exit /b 1
)

echo.
echo SUCCESS: Docker Compose stack started
echo.

REM PHASE 5: WAIT FOR SERVICES
echo [PHASE 5] Waiting for services to be ready...

timeout /t 5 /nobreak

REM Wait for main application
echo Waiting for RAG API...
set /a attempt=0
:wait_loop
if %attempt% geq 30 (
    echo ERROR: Application startup timeout
    exit /b 1
)

curl -s http://localhost:8000/api/health > nul 2>&1
if errorlevel 1 (
    set /a attempt=!attempt!+1
    timeout /t 2 /nobreak > nul
    goto wait_loop
)

echo SUCCESS: RAG API is ready
echo.

REM PHASE 6: TEST ENDPOINTS
echo [PHASE 6] Testing application endpoints...

echo Testing /api/health endpoint...
curl -s http://localhost:8000/api/health > nul && (
    echo SUCCESS: Health check passed
) || (
    echo ERROR: Health check failed
    exit /b 1
)

echo.

REM PHASE 7: DISPLAY STATUS
echo [PHASE 7] Docker Compose stack status:
docker-compose -f "%DOCKER_COMPOSE_FILE%" ps

echo.

REM PHASE 8: SUMMARY
echo ==========================================
echo SUCCESS: Docker deployment completed!
echo ==========================================
echo.

echo Available Endpoints:
echo   API:        http://localhost:8000
echo   Health:     http://localhost:8000/api/health
echo   Docs:       http://localhost:8000/docs
echo   Prometheus: http://localhost:9090
echo   PostgreSQL: localhost:5432
echo   Redis:      localhost:6379
echo.

echo Useful Commands:
echo   View logs:       docker-compose -f %DOCKER_COMPOSE_FILE% logs -f app
echo   Stop stack:      docker-compose -f %DOCKER_COMPOSE_FILE% down
echo   Clean volumes:   docker-compose -f %DOCKER_COMPOSE_FILE% down -v
echo   Restart app:     docker-compose -f %DOCKER_COMPOSE_FILE% restart app
echo.

echo To enable monitoring stack:
echo   docker-compose -f %DOCKER_COMPOSE_FILE% --profile monitoring up -d
echo.

echo To enable logging stack:
echo   docker-compose -f %DOCKER_COMPOSE_FILE% --profile logging up -d
echo.

echo Next steps:
echo   1. Check logs: docker-compose logs -f app
echo   2. Access API docs: http://localhost:8000/docs
echo   3. Create .env file from .env.example
echo   4. Update authentication credentials
echo   5. Enable monitoring for production
echo.

pause
