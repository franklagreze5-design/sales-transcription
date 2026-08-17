@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
)

set PYTHONPATH=%CD%\src
".venv\Scripts\python.exe" -m sales_transcriber.web_ui

pause
