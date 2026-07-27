# Однокомандный локальный запуск: .\start-local.ps1
# Окружением Python управляет uv (uv run сам синхронизирует зависимости по uv.lock).

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv не найден. Установка: winget install astral-sh.uv"
}

if (-not (Test-Path ".env")) {
    Copy-Item "templates/env.example" ".env"
    Write-Host "Создан .env из templates/env.example"
}

# ── Ollama ────────────────────────────────────────────────────────────────────

# Модель берётся из .env (OLLAMA_MODEL), дефолт совпадает с backend/config.py
$ollamaModel = "qwen2.5:1.5b"
$envLine = Select-String -Path ".env" -Pattern "^\s*OLLAMA_MODEL\s*=\s*(\S+)" | Select-Object -First 1
if ($envLine) { $ollamaModel = $envLine.Matches[0].Groups[1].Value }
if ($env:OLLAMA_MODEL) { $ollamaModel = $env:OLLAMA_MODEL }

function Test-Ollama {
    try {
        Invoke-RestMethod "http://localhost:11434/api/version" -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-Ollama)) {
    Write-Host "Запускаю Ollama..."
    $env:OLLAMA_NUM_PARALLEL = "1"
    $env:OLLAMA_MAX_LOADED_MODELS = "1"
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    $started = $false
    foreach ($i in 1..30) {
        if (Test-Ollama) { $started = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $started) {
        Write-Warning "Ollama не поднялась за 30 секунд — постобработка будет недоступна."
    }
}

if (Test-Ollama) {
    $models = ollama list
    if (-not ($models -match [regex]::Escape($ollamaModel))) {
        if ($ollamaModel -eq "transkreebatoriya-qwen25-cpu") {
            if (Test-Path ".\Modelfile.cpu-qwen25-1.5b") {
                Write-Host "Создаю модель $ollamaModel из Modelfile..."
                ollama create $ollamaModel -f .\Modelfile.cpu-qwen25-1.5b
            } else {
                Write-Warning "Modelfile.cpu-qwen25-1.5b не найден — запустите .\install.ps1 для генерации из templates/"
            }
        } else {
            Write-Host "Скачиваю модель $ollamaModel..."
            ollama pull $ollamaModel
        }
    }
}

# ── Приложение ────────────────────────────────────────────────────────────────

Write-Host "Запуск: http://localhost:8001"
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8001
