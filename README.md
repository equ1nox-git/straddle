# Straddle

A minimal Ollama proxy that gives every client — web UI, Siri shortcut, any script — a single consistent inference endpoint with persistent system prompt injection and KV cache tuning.

If you run Ollama locally and use more than one client, Straddle solves the problem of configuring each one separately.

![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/backend-Ollama-black?style=flat-square)

---

## What it does

**Single prompt source.** Edit `prompts/system_prompt.md` once. Every client that hits Straddle gets that context injected automatically — no per-client config, no duplicated prompt files.

**KV cache preservation.** Requests are forwarded to Ollama's native `/api/chat` with a fixed `num_ctx` and `keep_alive: -1`. The context window stays stable, the model stays resident in VRAM, and there's no cold-start reload between requests.

**Works with any OpenAI-compatible client.** Hermes WebUI, Siri shortcuts, curl, any SDK targeting `/v1/chat/completions`. Point them at Straddle instead of Ollama directly and they get prompt injection for free.

**~110 lines of Python.** No Docker, no npm, no config files. Just FastAPI + Ollama.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    YOUR CLIENTS                     │
│                                                     │
│       Hermes WebUI      Siri Shortcut      curl    │
└──────────┬───────────────┬──────────────┬──────────┘
           │               │              │
           └───────────────┴──────────────┘
                           │
                           ▼
           ┌───────────────────────────────┐
           │         STRADDLE :11435       │
           │                               │
           │  + inject system_prompt.md    │
           │  + inject master_context.md   │
           │  + fix num_ctx + keep_alive    │
           └───────────────┬───────────────┘
                           │
                           ▼
           ┌───────────────────────────────┐
           │          OLLAMA :11434        │
           │                               │
           │   local inference             │
           │   Vulkan compute              │
           └───────────────────────────────┘
```

---

## Quick start

```bash
git clone https://github.com/equ1nox-git/straddle.git
cd straddle
cp .env.example .env          # edit if your Ollama is not on localhost:11434
pip install -r requirements.txt
python3 api_server.py
```

Test it:
```bash
curl http://localhost:11435/v1/models
curl http://localhost:11435/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:7b","messages":[{"role":"user","content":"hello"}]}'
```

---

## Configuration

All settings via environment variables or `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama backend |
| `STRADDLE_HOST` | `0.0.0.0` | Bind address |
| `STRADDLE_PORT` | `11435` | Listen port |
| `DEFAULT_MODEL` | _(empty)_ | Fallback model when client sends none |
| `NUM_CTX` | `8192` | Context window (fixed — prevents KV buffer resize) |
| `KEEP_ALIVE` | `-1` | `-1` = keep model loaded forever, `0` = unload after each request |
| `PROMPTS_DIR` | `./prompts` | Directory containing `system_prompt.md` and `master_context.md` |

---

## Prompt files

| File | Purpose |
|------|---------|
| `prompts/system_prompt.md` | Base instructions injected on every request |
| `prompts/master_context.md` | Additional context appended after system prompt (excluded from repo — create locally) |

Both files are optional. If neither exists, requests pass through with no injection.

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/v1/models` | List Ollama models (OpenAI format) |
| `GET` | `/api/tags` | List Ollama models (Ollama native) |
| `POST` | `/v1/chat/completions` | Chat with system prompt injection, streaming supported |

---

## Systemd

```bash
systemctl --user enable --now straddle-api.service
systemctl --user status straddle-api
```

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) running on `localhost:11434`

---

## License

MIT
