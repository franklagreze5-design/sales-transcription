@echo off
setlocal
title Sales Intel Transcriber - Setup Coach IA

cd /d "%~dp0"

echo.
echo Sales Intel Transcriber - Setup Coach IA
echo ========================================
echo.
echo Este instalador prepara Ollama y descarga el modelo qwen3:1.7b.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-ollama-and-model.ps1"

echo.
echo Si el paso anterior termino correctamente, abre SalesIntelTranscriber.exe
echo.
pause
