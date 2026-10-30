@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Python-Umgebung fehlt. Bitte die Installation in docs\windows_vscode.md ausfuehren.
  pause
  exit /b 1
)
echo ServicePulse: Datenbank starten und pruefen ...
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\prepare_database.py"
if errorlevel 1 (
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -m streamlit run "%~dp0app.py" --server.address 127.0.0.1 %*
set "servicepulse_exit=%errorlevel%"
if not "%servicepulse_exit%"=="0" pause
exit /b %servicepulse_exit%
