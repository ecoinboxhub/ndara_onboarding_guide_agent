@echo off
REM ================================================================
REM ndara.ai Customer AI - Production Startup Script (Windows)
REM ================================================================

echo ========================================
echo ndara.ai Customer AI - Production Start
echo ========================================

REM Check if .env file exists
if not exist .env (
    echo Error: .env file not found!
    echo Please copy ENV_TEMPLATE.txt to .env and configure it.
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found. Creating...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Load environment variables from .env (requires python-dotenv)
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Environment loaded')"

REM Get configuration (defaults)
set API_HOST=0.0.0.0
set API_PORT=8000
set WORKERS=4
set LOG_LEVEL=info

echo Configuration:
echo   Host: %API_HOST%
echo   Port: %API_PORT%
echo   Workers: %WORKERS%
echo   Log Level: %LOG_LEVEL%
echo.

REM Start the server
echo Starting Customer AI server...
echo API will be available at: http://%API_HOST%:%API_PORT%
echo API Documentation: http://%API_HOST%:%API_PORT%/docs
echo.

gunicorn main:app ^
    --config gunicorn_config.py ^
    --bind %API_HOST%:%API_PORT% ^
    --workers %WORKERS% ^
    --worker-class uvicorn.workers.UvicornWorker ^
    --timeout 120 ^
    --access-logfile - ^
    --error-logfile - ^
    --log-level %LOG_LEVEL%

