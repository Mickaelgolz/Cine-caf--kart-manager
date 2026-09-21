@echo off
cd /d "%~dp0"
title CineCafe Kart Manager
if not exist ".venv\Scripts\python.exe" (
 call INSTALAR_WEB.bat
 if errorlevel 1 exit /b 1
)
.venv\Scripts\python.exe run_web.py
if errorlevel 1 pause
