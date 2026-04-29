@echo off
REM ============================================================
REM  Transkreebatoriya is launched by a single command
REM  Requirements: Python venv in backend\venv, ffmpeg in PATH,
REM              qwen3:4b runs in Ollama
REM ============================================================

cd /d "%~dp0"

echo [1/4] Checking Ollama availability...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo ERROR: Ollama not found. Run "ollama serve" in another terminal.
    pause
    exit /b 1
)
echo       OK

echo [2/4] Checking LLM availability...
curl -s http://localhost:11434/api/tags | findstr "qwen3:4b" >nul 2>&1
if errorlevel 1 (
    echo       qwen3:4b not found. Loading LLM...
    ollama pull qwen3:4b
)
echo       OK

echo [3/4] Checking Python dependencies...
cd backend
call venv\Scripts\activate.bat

python -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (
    echo       faster-whisper not found. Installing...
    pip install faster-whisper
    if errorlevel 1 (
        echo ERROR: Failed to install faster-whisper.
        pause
        exit /b 1
    )
    echo       faster-whisper installed.
) else (
    echo       faster-whisper OK
)

python -c "import dotenv" >nul 2>&1
if errorlevel 1 (
    echo       python-dotenv not found. Installing...
    pip install python-dotenv
)

echo       OK

echo [4/4] Running FastAPI backend...
REM --- Hugging Face token (you can skip adding a token, but it makes model download faster) ---
REM Set your HF token below (To obtain a new token, visit huggingface.co -> Settings -> Access Tokens):
REM set HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
REM -------------------------------------------------------------------------
REM --- Параллельная обработка чанков в Ollama ----------------------------
REM Разрешает Ollama обрабатывать несколько запросов одновременно (~2× быстрее).
REM Увеличьте POSTPROCESS_CONCURRENCY в backend/config.py если поднимаете выше 2.
set OLLAMA_NUM_PARALLEL=2
REM -----------------------------------------------------------------------
python -m uvicorn main:app --host localhost --port 8001 --reload --no-access-log

pause
