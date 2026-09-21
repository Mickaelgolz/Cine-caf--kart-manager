@echo off
cd /d "%~dp0"
title Compartilhar CineCafe
if not exist ".venv\Scripts\python.exe" (
 echo Abra INICIAR_WEB.bat primeiro.
 pause
 exit /b 1
)
.venv\Scripts\python.exe compartilhar.py
pause
