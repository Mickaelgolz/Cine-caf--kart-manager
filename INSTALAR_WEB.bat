@echo off
cd /d "%~dp0"
title Preparar CineCafe Kart Manager
where py >nul 2>nul
if errorlevel 1 (
 echo Instale Python 3.11 ou superior de https://www.python.org/downloads/windows/
 echo Depois abra este arquivo novamente.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if errorlevel 1 goto erro
.venv\Scripts\python.exe -m pip install -r requirements-web.txt
if errorlevel 1 goto erro
echo Pronto. Abra INICIAR_WEB.bat.
pause
exit /b 0
:erro
echo Nao foi possivel preparar. Confira Python e conexao com a internet.
pause
exit /b 1
