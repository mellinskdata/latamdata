@echo off
cd /d "%~dp0"
python -m pip install -r backend\requirements.txt
if errorlevel 1 (pause & exit /b 1)
python -m uvicorn backend.main:app --reload --port 8000
pause