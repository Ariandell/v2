@echo off
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
title Luna Music AI

echo.
echo  ╔══════════════════════════════════════╗
echo  ║       🎵  Luna Music AI  🎵         ║
echo  ╠══════════════════════════════════════╣
echo  ║  [1]  Start All (Backend + UI)       ║
echo  ║  [2]  Backend Only (FastAPI)         ║
echo  ║  [3]  Frontend Only (Vite/React)     ║
echo  ║  [0]  Exit                           ║
echo  ╚══════════════════════════════════════╝
echo.

set /p choice="Select option: "

if "%choice%"=="1" goto start_all
if "%choice%"=="2" goto start_backend
if "%choice%"=="3" goto start_frontend
if "%choice%"=="0" exit
goto :eof

:start_all
echo.
echo Starting Backend (FastAPI)...
if exist ".venv\Scripts\activate.bat" (
    start "Luna API Backend" /D "%~dp0" cmd /k "chcp 65001 >nul & set PYTHONUTF8=1& set PYTHONIOENCODING=utf-8& CALL .venv\Scripts\activate & python src\api\app.py"
) else (
    start "Luna API Backend" /D "%~dp0" cmd /k "chcp 65001 >nul & set PYTHONUTF8=1& set PYTHONIOENCODING=utf-8& python src\api\app.py"
)

timeout /t 3 /nobreak > nul

echo Starting Frontend (Vite/React)...
start "Luna UI Frontend" /D "%~dp0\ui" cmd /k "npm run dev"

echo.
echo Both services started!
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:1420
echo.
pause
goto :eof

:start_backend
echo.
echo Starting Backend (FastAPI)...
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)
python src\api\app.py
pause
goto :eof

:start_frontend
echo.
echo Starting Frontend (Vite/React)...
cd /d "%~dp0\ui"
npm run dev
pause
goto :eof
