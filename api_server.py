#!/usr/bin/env python3
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests, uvicorn, json, time, uuid

app = FastAPI()

OLLAMA_URL  = os.environ.get("OLLAMA_URL",   "http://localhost:11434")
HOST        = os.environ.get("STRADDLE_HOST", "0.0.0.0")
PORT        = int(os.environ.get("STRADDLE_PORT", 11435))
PROMPTS_DIR = Path(os.environ.get("PROMPTS_DIR", Path(__file__).parent / "prompts"))
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "")

OLLAMA_OPTIONS = {
    "num_ctx":    int(os.environ.get("NUM_CTX",    8192)),
    "keep_alive": int(os.environ.get("KEEP_ALIVE", -1)),
}

@app.get("/")
async def health():
    return {"status": "ok", "service": "straddle", "ollama": OLLAMA_URL}

def get_context() -> str:
    parts = []
    for name in ("system_prompt.md", "master_context.md"):
        p = PROMPTS_DIR / name
        if p.exists():
            parts.append(p.read_text())
    return "\n\nContext:\n".join(parts)

def build_ollama_messages(messages: list, extra_system: str) -> tuple[str, list]:
    # Hoist system-role entries into a single stable system block so Ollama
    # can maximise KV prefix reuse across requests.
    system_parts = [extra_system] if extra_system else []
    conv = []
    for m in messages:
        role    = m.get("role", "user")
        content = m.get("content", "") or ""
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        if role == "system":
            system_parts.append(content)
        else:
            conv.append({"role": role, "content": content})
    return "\n\n".join(filter(None, system_parts)), conv

@app.get("/v1/models")
async def list_models_openai():
    res = requests.get(f"{OLLAMA_URL}/api/tags").json()
    models = [{"id": m["name"], "object": "model", "owned_by": "ollama"} for m in res.get("models", [])]
    return {"object": "list", "data": models}

@app.get("/api/tags")
async def list_models():
    return requests.get(f"{OLLAMA_URL}/api/tags").json()

class ChatRequest(BaseModel):
    model:       str  = DEFAULT_MODEL
    messages:    list
    stream:      bool = False
    tools:       list = []
    tool_choice: str  = "auto"

def stream_ollama(model: str, messages: list, ctx: str):
    cid     = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    system, conv = build_ollama_messages(messages, ctx)
    with requests.post(f"{OLLAMA_URL}/api/chat", json={
        "model": model, "messages": conv, "system": system,
        "stream": True, "options": OLLAMA_OPTIONS,
    }, stream=True) as resp:
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            token = chunk.get("message", {}).get("content", "")
            done  = chunk.get("done", False)
            sse = {
                "id": cid, "object": "chat.completion.chunk",
                "created": created, "model": model,
                "choices": [{"index": 0, "delta": {"content": token},
                             "finish_reason": "stop" if done else None}],
            }
            yield f"data: {json.dumps(sse)}\n\n"
            if done:
                yield "data: [DONE]\n\n"
                return

@app.post("/v1/chat/completions")
async def chat(request: ChatRequest):
    ctx = get_context()
    if request.stream:
        return StreamingResponse(
            stream_ollama(request.model, request.messages, ctx),
            media_type="text/event-stream",
        )
    system, conv = build_ollama_messages(request.messages, ctx)
    resp = requests.post(f"{OLLAMA_URL}/api/chat", json={
        "model": request.model, "messages": conv, "system": system,
        "stream": False, "options": OLLAMA_OPTIONS,
    })
    content = resp.json().get("message", {}).get("content", "")
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
