$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path ".\.venv\Scripts\pyinstaller.exe")) {
    .\.venv\Scripts\python.exe -m pip install pyinstaller
}

.\.venv\Scripts\pyinstaller.exe `
    --name SalesIntelTranscriber `
    --onedir `
    --noconfirm `
    --additional-hooks-dir "pyinstaller_hooks" `
    --add-data "src\sales_transcriber\web_static;sales_transcriber\web_static" `
    --add-data ".venv\Lib\site-packages\faster_whisper\assets;faster_whisper\assets" `
    --exclude-module pyannote `
    --exclude-module speechbrain `
    --exclude-module torch `
    --exclude-module torchaudio `
    --exclude-module torchvision `
    --exclude-module tensorflow `
    --exclude-module matplotlib `
    --exclude-module pandas `
    --exclude-module scipy `
    --exclude-module sklearn `
    --paths "src" `
    src\sales_transcriber\web_ui.py

Write-Host ""
Write-Host "EXE creado en: dist\SalesIntelTranscriber\SalesIntelTranscriber.exe"

Copy-Item -LiteralPath ".\install-ollama-and-model.ps1" `
    -Destination ".\dist\SalesIntelTranscriber\install-ollama-and-model.ps1" `
    -Force

Copy-Item -LiteralPath ".\INSTALAR_CLIENTE.txt" `
    -Destination ".\dist\SalesIntelTranscriber\INSTALAR_CLIENTE.txt" `
    -Force

Write-Host "Archivos de instalacion cliente copiados a dist\SalesIntelTranscriber"
