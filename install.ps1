# Установка Transkreebatoriya (Windows): .\install.ps1
#
# Что делает:
#   1. Проверяет зависимости (uv, ffmpeg, Ollama).
#   2. Создаёт .env из templates/env.example — НЕ перезаписывает существующий.
#   3. Рендерит Modelfile.cpu-qwen25-1.5b из templates/ по значениям .env —
#      НЕ перезаписывает существующий.
#   4. Синхронизирует Python-зависимости (uv sync).
#   5. Скачивает/создаёт модель Ollama (если Ollama доступна).
#
# Повторный запуск безопасен: существующие локальные конфиги пропускаются.

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Skip($msg) { Write-Host "    skip: $msg" -ForegroundColor DarkGray }

# ── 1. Зависимости ────────────────────────────────────────────────────────────

Write-Step "Проверка зависимостей"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv не найден. Установка: winget install astral-sh.uv"
    exit 1
}
Write-Host "    uv: OK"

if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "    ffmpeg: OK"
} else {
    Write-Warning "ffmpeg не найден в PATH. Установите ffmpeg или задайте FFMPEG_PATH в .env"
}

$ollamaCli = [bool](Get-Command ollama -ErrorAction SilentlyContinue)
if ($ollamaCli) {
    Write-Host "    ollama: OK"
} else {
    Write-Warning "Ollama не найдена. Постобработка будет недоступна: https://ollama.com"
}

# ── 2. .env из шаблона (never overwrite) ──────────────────────────────────────

Write-Step "Конфигурация"

if (Test-Path ".env") {
    Write-Skip ".env уже существует — не перезаписываю"
} else {
    # Минимальный .env: только активные переменные из шаблона, без комментариев
    $vars = Get-Content "templates/env.example" | Where-Object { $_ -match "^[A-Z][A-Z0-9_]*=" }
    [System.IO.File]::WriteAllLines((Join-Path (Get-Location) ".env"), $vars, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "    создан .env (только переменные) из templates/env.example"
}

# Чтение значения из .env / окружения с дефолтом
function Get-EnvValue([string]$name, [string]$default) {
    $envVar = Get-Item "Env:$name" -ErrorAction SilentlyContinue
    if ($envVar) { return $envVar.Value }
    if (Test-Path ".env") {
        $line = Select-String -Path ".env" -Pattern "^\s*$name\s*=\s*(\S+)" | Select-Object -First 1
        if ($line) { return $line.Matches[0].Groups[1].Value }
    }
    return $default
}

# ── 3. Modelfile из шаблона (never overwrite) ─────────────────────────────────

$modelfileOut = "Modelfile.cpu-qwen25-1.5b"
if (Test-Path $modelfileOut) {
    Write-Skip "$modelfileOut уже существует — не перезаписываю"
} else {
    $defaults = @{
        OLLAMA_NUM_CTX = "2048"; OLLAMA_NUM_PREDICT = "768"; OLLAMA_TEMPERATURE = "0.15"
        OLLAMA_TOP_P = "0.9"; OLLAMA_TOP_K = "30"; OLLAMA_MIN_P = "0.05"
        OLLAMA_REPEAT_LAST_N = "128"; OLLAMA_REPEAT_PENALTY = "1.08"
    }
    # Явная UTF-8: Get-Content/Set-Content в PS 5.1 по умолчанию используют ANSI
    $templatePath = Join-Path (Get-Location) "templates/Modelfile.cpu-qwen25-1.5b.template"
    $rendered = [System.IO.File]::ReadAllText($templatePath, [System.Text.Encoding]::UTF8)
    foreach ($var in $defaults.Keys) {
        $rendered = $rendered -replace [regex]::Escape("{{$var}}"), (Get-EnvValue $var $defaults[$var])
    }
    # Modelfile пишем в UTF-8 без BOM — ollama create может споткнуться о BOM
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText((Join-Path (Get-Location) $modelfileOut), $rendered, $utf8NoBom)
    Write-Host "    создан $modelfileOut из templates/"
}

# ── 4. Python-зависимости ─────────────────────────────────────────────────────

Write-Step "Python-зависимости (uv sync)"
uv sync --frozen

# ── 5. Модель Ollama ──────────────────────────────────────────────────────────

$ollamaModel = Get-EnvValue "OLLAMA_MODEL" "qwen2.5:1.5b"

function Test-Ollama {
    try {
        Invoke-RestMethod "http://localhost:11434/api/version" -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

if ($ollamaCli -and (Test-Ollama)) {
    Write-Step "Модель Ollama: $ollamaModel"
    $models = ollama list
    if ($models -match [regex]::Escape($ollamaModel)) {
        Write-Skip "модель $ollamaModel уже есть"
    } elseif ($ollamaModel -eq "transkreebatoriya-qwen25-cpu") {
        Write-Host "    создаю $ollamaModel из $modelfileOut..."
        ollama create $ollamaModel -f ".\$modelfileOut"
    } else {
        Write-Host "    скачиваю $ollamaModel..."
        ollama pull $ollamaModel
    }
} else {
    Write-Skip "Ollama недоступна — модель не скачана (повторите после запуска Ollama)"
}

# ── Итог ──────────────────────────────────────────────────────────────────────

Write-Step "Установка завершена"
Write-Host "    Проверка:  .\scripts\verify_install.ps1"
Write-Host "    Запуск:    .\start-local.ps1   (или: uv run uvicorn backend.main:app --port 8001)"
