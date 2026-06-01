@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "APP_DIR=%ROOT_DIR%career_agent"
set "VENV_ACTIVATE=%ROOT_DIR%.venv\Scripts\activate.bat"

if not exist "%APP_DIR%\backend\main.py" (
    echo [ERROR] Cannot find backend entry: "%APP_DIR%\backend\main.py"
    pause
    exit /b 1
)

if not exist "%APP_DIR%\frontend\app.py" (
    echo [ERROR] Cannot find frontend entry: "%APP_DIR%\frontend\app.py"
    pause
    exit /b 1
)

if not exist "%VENV_ACTIVATE%" (
    echo [ERROR] Cannot find virtual environment: "%VENV_ACTIVATE%"
    echo Please create it first:
    echo   python -m venv .venv
    echo   .\.venv\Scripts\activate
    echo   pip install -r .\career_agent\requirements.txt
    pause
    exit /b 1
)

echo Starting Career Agent backend...
start "Career Agent Backend" cmd /k "cd /d ""%APP_DIR%"" && call ""%VENV_ACTIVATE%"" && uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

echo Starting Career Agent frontend...
start "Career Agent Frontend" cmd /k "cd /d ""%APP_DIR%"" && call ""%VENV_ACTIVATE%"" && streamlit run frontend/app.py"

echo.
echo Backend:  http://127.0.0.1:8000
echo Frontend: Streamlit will print the local URL in the frontend window.
echo.
pause
