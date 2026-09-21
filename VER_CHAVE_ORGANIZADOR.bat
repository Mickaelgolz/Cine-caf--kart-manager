@echo off
cd /d "%~dp0"
if exist data\CHAVE_ORGANIZADOR.txt (notepad data\CHAVE_ORGANIZADOR.txt) else (echo Abra o programa primeiro. & pause)
