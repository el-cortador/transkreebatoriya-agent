#!/usr/bin/env bash
# Установка Transkreebatoriya (Linux/macOS): ./install.sh
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

set -euo pipefail
cd "$(dirname "$0")"

step() { printf '\033[36m==> %s\033[0m\n' "$1"; }
skip() { printf '    skip: %s\n' "$1"; }
warn() { printf '\033[33m    warn: %s\033[0m\n' "$1"; }

# ── 1. Зависимости ────────────────────────────────────────────────────────────

step "Проверка зависимостей"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv не найден. Установка: https://docs.astral.sh/uv/" >&2
    exit 1
fi
echo "    uv: OK"

if command -v ffmpeg >/dev/null 2>&1; then
    echo "    ffmpeg: OK"
else
    warn "ffmpeg не найден в PATH. Установите ffmpeg или задайте FFMPEG_PATH в .env"
fi

OLLAMA_CLI=0
if command -v ollama >/dev/null 2>&1; then
    OLLAMA_CLI=1
    echo "    ollama: OK"
else
    warn "Ollama не найдена. Постобработка будет недоступна: https://ollama.com"
fi

# ── 2. .env из шаблона (never overwrite) ──────────────────────────────────────

step "Конфигурация"

if [[ -f .env ]]; then
    skip ".env уже существует — не перезаписываю"
else
    # Минимальный .env: только активные переменные из шаблона, без комментариев
    grep -E '^[A-Z][A-Z0-9_]*=' templates/env.example > .env
    echo "    создан .env (только переменные) из templates/env.example"
fi

# Чтение значения из окружения / .env с дефолтом
env_value() {
    local name="$1" default="$2" value=""
    value="${!name:-}"
    if [[ -z "$value" && -f .env ]]; then
        value=$(grep -E "^\s*${name}\s*=" .env | head -n1 | cut -d= -f2- | tr -d '[:space:]')
    fi
    printf '%s' "${value:-$default}"
}

# ── 3. Modelfile из шаблона (never overwrite) ─────────────────────────────────

MODELFILE_OUT="Modelfile.cpu-qwen25-1.5b"
if [[ -f "$MODELFILE_OUT" ]]; then
    skip "$MODELFILE_OUT уже существует — не перезаписываю"
else
    rendered=$(cat "templates/Modelfile.cpu-qwen25-1.5b.template")
    for var in OLLAMA_NUM_CTX:2048 OLLAMA_NUM_PREDICT:768 OLLAMA_TEMPERATURE:0.15 \
               OLLAMA_TOP_P:0.9 OLLAMA_TOP_K:30 OLLAMA_MIN_P:0.05 \
               OLLAMA_REPEAT_LAST_N:128 OLLAMA_REPEAT_PENALTY:1.08; do
        name="${var%%:*}"; default="${var##*:}"
        rendered="${rendered//\{\{$name\}\}/$(env_value "$name" "$default")}"
    done
    printf '%s\n' "$rendered" > "$MODELFILE_OUT"
    echo "    создан $MODELFILE_OUT из templates/"
fi

# ── 4. Python-зависимости ─────────────────────────────────────────────────────

step "Python-зависимости (uv sync)"
uv sync --frozen

# ── 5. Модель Ollama ──────────────────────────────────────────────────────────

OLLAMA_MODEL=$(env_value OLLAMA_MODEL "qwen2.5:1.5b")

ollama_up() { curl -sf --max-time 2 http://localhost:11434/api/version >/dev/null 2>&1; }

if [[ "$OLLAMA_CLI" == "1" ]] && ollama_up; then
    step "Модель Ollama: $OLLAMA_MODEL"
    if ollama list | grep -qF "$OLLAMA_MODEL"; then
        skip "модель $OLLAMA_MODEL уже есть"
    elif [[ "$OLLAMA_MODEL" == "transkreebatoriya-qwen25-cpu" ]]; then
        echo "    создаю $OLLAMA_MODEL из $MODELFILE_OUT..."
        ollama create "$OLLAMA_MODEL" -f "./$MODELFILE_OUT"
    else
        echo "    скачиваю $OLLAMA_MODEL..."
        ollama pull "$OLLAMA_MODEL"
    fi
else
    skip "Ollama недоступна — модель не скачана (повторите после запуска Ollama)"
fi

# ── Итог ──────────────────────────────────────────────────────────────────────

step "Установка завершена"
echo "    Проверка:  ./scripts/verify_install.sh"
echo "    Запуск:    uv run uvicorn backend.main:app --host 0.0.0.0 --port 8001"
