# Straddle

OpenAI-compatible FastAPI proxy gateway for local Ollama inference. Injects system prompt and personal context on every request. Includes Telegram bot gateway.

## Architecture

```
Client (OpenAI API) → Straddle :11435 → Ollama :11434 (local)
Telegram → telegram_gateway.py → Straddle :11435 → Ollama :11434
```

## Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/models` | List available Ollama models (OpenAI format) |
| GET | `/api/tags` | List available Ollama models (native format) |
| POST | `/v1/chat/completions` | Chat completions with system prompt injection (streaming supported) |

## Setup

```bash
cp .env.example .env
# Edit .env and set TELEGRAM_BOT_TOKEN
pip install -r requirements.txt
python3 api_server.py
```

## Systemd

```bash
systemctl --user enable --now straddle-api.service
systemctl --user enable --now straddle-bot.service
```

## Prompts

- `prompts/system_prompt.md` — base system prompt injected on every request
- `prompts/master_context.md` — personal context appended to system prompt (excluded from repo; create locally)

## Requirements

- Ollama running on `localhost:11434`
- Python 3.10+
