@echo off
setlocal
set PY="C:\Program Files\Odoo 17.0.20260103\python\python.exe"
cd /d "%~dp0"
%PY% main.py
if errorlevel 1 pause
endlocal