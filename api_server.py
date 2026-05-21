#!/usr/bin/env python3
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests, uvicorn, json, time, uuid

app = FastAPI()

# Stable Ollama options — fixed num_ctx prevents buffer resize on skill load;
# keep_alive=-1 keeps model warm between requests.
OLLAMA_OPTIONS = {
    "num_ctx": 8192,
    "keep_alive": -1,
}

def get_context():
    with open("/home/thomasb/straddle/prompts/system_prompt.md") as f: sys = f.read()
    with open("/home/thomasb/straddle/prompts/master_context.md") as f: ctx = f.read()
    return f"{sys}\n\nContext: {ctx}"

def build_ollama_messages(messages: list, extra_system: str) -> tuple[str, list]:
    """
    Split OpenAI messages into (system_prompt, conversation_messages).
    System-role entries are hoisted to top and merged with extra_system so
    Ollama sees a single stable system block — maximises KV prefix reuse.
    """
    system_parts = [extra_system]
    conv = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "") or ""
        if isinstance(content, list):
            # Flatten tool/content-array to plain text
            content = " ".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )
        if role == "system":
            system_parts.append(content)
        else:
            conv.append({"role": role, "content": content})
    return "\n\n".join(filter(None, system_parts)), conv

@app.get("/v1/models")
async def list_models_openai():
    res = requests.get("http://localhost:11434/api/tags").json()
    models = [{"id": m["name"], "object": "model", "owned_by": "ollama"} for m in res.get("models", [])]
    return {"object": "list", "data": models}

@app.get("/api/tags")
async def list_models():
    return requests.get("http://localhost:11434/api/tags").json()

class ChatRequest(BaseModel):
    model: str
    messages: list
    stream: bool = False
    tools: list = []          # accepted but not forwarded (Ollama handles natively)
    tool_choice: str = "auto" # accepted, ignored

def stream_ollama(model: str, messages: list, ctx: str):
    cid = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    system, conv = build_ollama_messages(messages, ctx)

    with requests.post("http://localhost:11434/api/chat", json={
        "model": model,
        "messages": conv,
        "system": system,
        "stream": True,
        "options": OLLAMA_OPTIONS,
    }, stream=True) as resp:
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            token = chunk.get("message", {}).get("content", "")
            done = chunk.get("done", False)

            sse = {
                "id": cid,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": "stop" if done else None}]
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
            media_type="text/event-stream"
        )
    system, conv = build_ollama_messages(request.messages, ctx)
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": request.model,
        "messages": conv,
        "system": system,
        "stream": False,
        "options": OLLAMA_OPTIONS,
    })
    content = resp.json().get("message", {}).get("content", "")
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=11435)
