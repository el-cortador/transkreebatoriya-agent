#!/usr/bin/env bash
# Проверка установки Transkreebatoriya (Linux/macOS): ./scripts/verify_install.sh
# Вывод: [OK] / [WARN] / [FAIL] по каждой проверке.
# Код выхода: 1, если есть хотя бы один [FAIL].

cd "$(dirname "$0")/.."

failures=0

ok()   { printf '\033[32m[OK]\033[0m   %s\n' "$1"; }
warn() { printf '\033[33m[WARN]\033[0m %s\n' "$1"; }
fail() { printf '\033[31m[FAIL]\033[0m %s\n' "$1"; failures=$((failures + 1)); }

# ── Обязательные компоненты ───────────────────────────────────────────────────

if command -v uv >/dev/null 2>&1; then
    ok "uv установлен"
else
    fail "uv не найден — установка: https://docs.astral.sh/uv/"
fi

if command -v ffmpeg >/dev/null 2>&1; then
    ok "ffmpeg доступен в PATH"
else
    fail "ffmpeg не найден — установите ffmpeg или задайте FFMPEG_PATH в .env"
fi

if uv run python -c "import fastapi, faster_whisper, httpx, pydantic_settings" >/dev/null 2>&1; then
    ok "Python-зависимости установлены (uv)"
else
    fail "Python-зависимости не установлены — выполните: uv sync --frozen"
fi

if [[ -f core/prompts/postprocess.system.md ]]; then
    ok "core-промпты на месте"
else
    fail "core/prompts/postprocess.system.md не найден — репозиторий повреждён?"
fi

if [[ -f manifest.yaml ]]; then
    ok "manifest.yaml на месте"
else
    fail "manifest.yaml не найден"
fi

mkdir -p temp
if touch temp/.write-probe 2>/dev/null; then
    rm -f temp/.write-probe
    ok "temp/ доступна на запись"
else
    fail "temp/ недоступна на запись"
fi

# ── Конфигурация ──────────────────────────────────────────────────────────────

if [[ -f .env ]]; then
    ok ".env существует"
else
    warn ".env отсутствует — будут использованы дефолты (install.sh создаёт его из templates/)"
fi

# ── Опциональные компоненты (постобработка) ───────────────────────────────────

if curl -sf --max-time 2 http://localhost:11434/api/version >/dev/null 2>&1; then
    ok "Ollama отвечает (localhost:11434)"

    ollama_model="qwen2.5:1.5b"
    if [[ -f .env ]]; then
        from_env=$(grep -E '^\s*OLLAMA_MODEL\s*=' .env | head -n1 | cut -d= -f2- | tr -d '[:space:]')
        [[ -n "$from_env" ]] && ollama_model="$from_env"
    fi
    [[ -n "${OLLAMA_MODEL:-}" ]] && ollama_model="$OLLAMA_MODEL"

    if ollama list 2>/dev/null | grep -qF "$ollama_model"; then
        ok "модель Ollama '$ollama_model' скачана"
    else
        warn "модель Ollama '$ollama_model' не скачана — выполните: ollama pull $ollama_model"
    fi
else
    warn "Ollama недоступна — транскрибация работает, постобработка нет"
fi

# ── Итог ──────────────────────────────────────────────────────────────────────

echo
if [[ $failures -gt 0 ]]; then
    printf '\033[31mПроверок не пройдено: %s. См. docs/TROUBLESHOOTING.md\033[0m\n' "$failures"
    exit 1
else
    printf '\033[32mУстановка в порядке. Smoke test: docs/SMOKE_TEST_PLAN.md\033[0m\n'
fi
