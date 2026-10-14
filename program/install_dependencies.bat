@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements_lock.txt
if errorlevel 1 goto failed
echo Installation completed. Run run_analysis.bat.
pause
exit /b 0
:failed
echo Installation failed. Please ensure Python 3.12 is installed and inspect the error above.
pause
exit /b 1
