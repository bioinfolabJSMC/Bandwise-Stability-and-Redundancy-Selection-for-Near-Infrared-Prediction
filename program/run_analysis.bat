@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" run_all.py
if errorlevel 1 goto failed
echo Completed. Open the results folder.
pause
exit /b 0
:missing
echo Run install_dependencies.bat first.
pause
exit /b 1
:failed
echo Analysis failed. Inspect the error above.
pause
exit /b 1
