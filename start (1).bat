@echo off
echo =======================================================
echo   PayLens — Iniciando proyecto completo
echo =======================================================

echo.
echo [1/2] Iniciando Login (puerto 5000)...
start "PayLens Login" cmd /k "cd /d D:\Proyecto^ Pia\Proyecto^ Pia\login && venv\Scripts\activate && python main.py"

timeout /t 2 /nobreak > nul

echo [2/2] Iniciando PayLens Backend (puerto 8000)...
start "PayLens Backend" cmd /k "cd /d D:\Proyecto^ Pia\Proyecto^ Pia\comprobante-backend && venv311\Scripts\activate && python run.py"

echo.
echo =======================================================
echo   Listo! Abre tu navegador en:
echo   http://localhost:5000
echo =======================================================
pause