# Проверка установки Transkreebatoriya (Windows): .\scripts\verify_install.ps1
# Вывод: [OK] / [WARN] / [FAIL] по каждой проверке.
# Код выхода: 1, если есть хотя бы один [FAIL].

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

$script:failures = 0

function Check-Ok($msg)   { Write-Host "[OK]   $msg" -ForegroundColor Green }
function Check-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Check-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; $script:failures++ }

# ── Обязательные компоненты ───────────────────────────────────────────────────

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Check-Ok "uv установлен"
} else {
    Check-Fail "uv не найден — установка: winget install astral-sh.uv"
}

if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Check-Ok "ffmpeg доступен в PATH"
} else {
    Check-Fail "ffmpeg не найден — установите ffmpeg или задайте FFMPEG_PATH в .env"
}

# Python-зависимости синхронизированы
$depsCheck = uv run python -c "import fastapi, faster_whisper, httpx, pydantic_settings" 2>&1
if ($LASTEXITCODE -eq 0) {
    Check-Ok "Python-зависимости установлены (uv)"
} else {
    Check-Fail "Python-зависимости не установлены — выполните: uv sync --frozen"
}

# Core-файлы агента
if (Test-Path "core/prompts/postprocess.system.md") {
    Check-Ok "core-промпты на месте"
} else {
    Check-Fail "core/prompts/postprocess.system.md не найден — репозиторий повреждён?"
}

if (Test-Path "manifest.yaml") {
    Check-Ok "manifest.yaml на месте"
} else {
    Check-Fail "manifest.yaml не найден"
}

# Директория temp существует и доступна на запись
try {
    New-Item -ItemType Directory -Force -Path "temp" | Out-Null
    $probe = "temp\.write-probe"
    Set-Content $probe "ok" -ErrorAction Stop
    Remove-Item $probe
    Check-Ok "temp/ доступна на запись"
} catch {
    Check-Fail "temp/ недоступна на запись: $_"
}

# ── Конфигурация ──────────────────────────────────────────────────────────────

if (Test-Path ".env") {
    Check-Ok ".env существует"
} else {
    Check-Warn ".env отсутствует — будут использованы дефолты (install.ps1 создаёт его из templates/)"
}

# ── Опциональные компоненты (постобработка) ───────────────────────────────────

$ollamaUp = $false
try {
    Invoke-RestMethod "http://localhost:11434/api/version" -TimeoutSec 2 | Out-Null
    $ollamaUp = $true
    Check-Ok "Ollama отвечает (localhost:11434)"
} catch {
    Check-Warn "Ollama недоступна — транскрибация работает, постобработка нет"
}

if ($ollamaUp) {
    $ollamaModel = "qwen2.5:1.5b"
    if (Test-Path ".env") {
        $line = Select-String -Path ".env" -Pattern "^\s*OLLAMA_MODEL\s*=\s*(\S+)" | Select-Object -First 1
        if ($line) { $ollamaModel = $line.Matches[0].Groups[1].Value }
    }
    if ($env:OLLAMA_MODEL) { $ollamaModel = $env:OLLAMA_MODEL }

    if ((ollama list) -match [regex]::Escape($ollamaModel)) {
        Check-Ok "модель Ollama '$ollamaModel' скачана"
    } else {
        Check-Warn "модель Ollama '$ollamaModel' не скачана — выполните: ollama pull $ollamaModel"
    }
}

# ── Итог ──────────────────────────────────────────────────────────────────────

Write-Host ""
if ($script:failures -gt 0) {
    Write-Host "Проверок не пройдено: $($script:failures). См. docs/TROUBLESHOOTING.md" -ForegroundColor Red
    exit 1
} else {
    Write-Host "Установка в порядке. Smoke test: docs/SMOKE_TEST_PLAN.md" -ForegroundColor Green
}
