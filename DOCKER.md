# Docker run

Docker is the simplest isolated setup: the app container includes Python dependencies and ffmpeg,
and a separate Ollama container stores models in a Docker volume.

## Start

```powershell
docker compose up --build
```

Open:

```text
http://localhost:8001
```

The first run is slow because Docker builds the app image, Ollama downloads `qwen2.5:1.5b`
(or the model set in `OLLAMA_MODEL`), and faster-whisper downloads the Whisper model on first transcription.

## Stop

```powershell
docker compose down
```

To remove downloaded Docker volumes too:

```powershell
docker compose down -v
```

## Configuration

Use environment variables or a root `.env` file (full template with comments:
`templates/env.example` — install scripts copy it to `.env` without overwriting):

```dotenv
APP_PORT=8001
OLLAMA_PORT=11434
OLLAMA_MODEL=qwen3:4b
WHISPER_MODEL_NAME=base
WHISPER_DEVICE=auto
WHISPER_LANGUAGE=ru
POSTPROCESS_CONCURRENCY=2
OLLAMA_NUM_PARALLEL=2
MAX_FILE_SIZE_GB=6
TASK_TTL_HOURS=24
```

Inside Docker, `OLLAMA_API_URL` is set to `http://ollama:11434/api/generate`.
