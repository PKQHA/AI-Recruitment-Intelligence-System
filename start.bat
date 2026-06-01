@echo off

cd /d %~dp0

call .venv\Scripts\activate

start cmd /k "uvicorn backend.main:app --reload"
start cmd /k "streamlit run frontend/app.py"

pause