$ErrorActionPreference = "Stop"

$model = "qwen3:1.7b"

Write-Host ""
Write-Host "Sales Intel Transcriber - Setup de Coach IA"
Write-Host "=========================================="
Write-Host ""

$ollama = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $ollama) {
    Write-Host "Ollama no esta instalado."
    Write-Host "Abriendo la pagina oficial de descarga..."
    Start-Process "https://ollama.com/download/windows"
    Write-Host ""
    Write-Host "Instala Ollama para Windows y vuelve a ejecutar este archivo."
    Write-Host ""
    pause
    exit 1
}

Write-Host "Ollama encontrado: $($ollama.Source)"
Write-Host "Verificando servidor local..."

try {
    Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5 | Out-Null
} catch {
    Write-Host "Iniciando Ollama..."
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

Write-Host "Descargando/verificando modelo $model..."
ollama pull $model

Write-Host ""
Write-Host "Listo. Ahora puedes abrir SalesIntelTranscriber.exe."
Write-Host ""
pause
