@echo off
cd /d "%~dp0frontend"
where npm >nul 2>&1
if errorlevel 1 (
    echo Node.js nao encontrado. Instale Node.js 22 LTS.
    pause
    exit /b 1
)
if not exist node_modules (
    echo Instalando dependencias do site...
    call npm install
    if errorlevel 1 (pause & exit /b 1)
)
echo Iniciando LATAMDATA...
call npm run dev
pause