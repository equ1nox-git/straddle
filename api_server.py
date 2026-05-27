#!/usr/bin/env python3
import os, subprocess, re
from pathlib import Path
from fastapi import FastAPI, HTTPException, Security
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import requests, uvicorn, json, time, uuid
from fastapi import Depends

app = FastAPI()

OLLAMA_URL    = os.environ.get("OLLAMA_URL",   "http://localhost:11434")
HOST          = os.environ.get("STRADDLE_HOST", "100.118.201.46")
PORT          = int(os.environ.get("STRADDLE_PORT", 11435))
API_KEY       = os.environ.get("STRADDLE_API_KEY", "")

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(key: str = Security(_api_key_header)):
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key
PROMPTS_DIR   = Path(os.environ.get("PROMPTS_DIR", Path(__file__).parent / "prompts"))
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "")
HIMALAYA      = os.path.expanduser("~/.local/bin/himalaya")
HERMESCAL     = "/home/thomasb/straddle/hermescal.py"

OLLAMA_OPTIONS = {
    "num_ctx":    int(os.environ.get("NUM_CTX",    8192)),
    "keep_alive": int(os.environ.get("KEEP_ALIVE", -1)),
}

# ---------------------------------------------------------------------------
# Data injection patterns — run real commands, inject results as context
# ---------------------------------------------------------------------------

SEND_EMAIL_RE = re.compile(
    r'\b(send|write|compose|draft)\b.{0,20}\b(email|mail)\b', re.I
)

EMAIL_PATTERNS = [
    (r'\b(list|show|get|check|fetch|read|summarize)\b.{0,40}\b(email|inbox|mail)\b', None),
    (r'\b(email|inbox|mail)\b.{0,40}\b(list|show|get|check|fetch|last|recent|summarize)\b', None),
    (r'\blast \d+ email', None),
]

CALENDAR_PATTERNS = [
    (r'\b(calendar|event|events|schedule|upcoming)\b', None),
    (r'\bcoming up\b', None),
    (r'\b(this week|next week|this weekend|today|tomorrow)\b', None),
    (r'\b(busy|free|plans|agenda)\b', None),
    (r'\b(reminder|reminders)\b', None),
    (r'\bwhat do i have\b', None),
    (r'\bwhat.{0,10}(week|weekend|today|tomorrow)\b', None),
]

def _run(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return f"error: {e}"

def _detect_account(text: str) -> str:
    t = text.lower()
    if "gmail" in t: return "gmail"
    if "yahoo" in t: return "yahoo"
    return "icloud"

def _parse_send_intent(text: str) -> dict | None:
    """Extract to/subject/body/account from send email request."""
    to_m      = re.search(r'\bto\b\s+([\w.+@\-]+)', text, re.I)
    subj_m    = re.search(r'\bsubject\b\s+"([^"]+)"', text, re.I) or \
                re.search(r'\bsubject\b\s+["\']?([^"\']+?)["\']?\s+(body|$)', text, re.I)
    body_m    = re.search(r'\bbody\b\s+"([^"]+)"', text, re.I) or \
                re.search(r'\bbody\b\s+["\']?([^"\']+)["\']?$', text, re.I)
    account   = _detect_account(text)
    to        = to_m.group(1) if to_m else None
    subject   = subj_m.group(1).strip() if subj_m else "No subject"
    body      = body_m.group(1).strip() if body_m else ""
    return {"to": to, "subject": subject, "body": body, "account": account} if to else None

def inject_data(last_user_msg: str) -> str | None:
    """Return injected context string if message matches known data patterns."""
    msg = last_user_msg.lower()

    # Send email — execute and return result
    if SEND_EMAIL_RE.search(last_user_msg):
        intent = _parse_send_intent(last_user_msg)
        if intent:
            account_emails = {
                "icloud": "tom.mb99@icloud.com",
                "gmail":  "tmb129129@gmail.com",
                "yahoo":  "tmb199922@yahoo.com",
            }
            from_addr = account_emails.get(intent["account"], "tom.mb99@icloud.com")
            mime = "\n".join([
                f"From: {from_addr}",
                f"To: {intent['to']}",
                f"Subject: {intent['subject']}",
                "",
                intent["body"],
            ])
            try:
                proc = subprocess.run(
                    [HIMALAYA, "template", "send", "-a", intent["account"]],
                    input=mime, capture_output=True, text=True, timeout=30
                )
                out = (proc.stdout + proc.stderr).strip()
                status = "sent successfully" if proc.returncode == 0 else f"failed: {out}"
            except Exception as e:
                status = f"failed: {e}"
            return f"[EMAIL SEND RESULT]\nTo: {intent['to']} | Subject: {intent['subject']} | Status: {status}"

    for pat, _ in EMAIL_PATTERNS:
        if re.search(pat, msg):
            account = _detect_account(last_user_msg)
            m = re.search(r'last (\d+)', msg)
            count = m.group(1) if m else "5"
            out = _run([HIMALAYA, "envelope", "list", "-a", account, "-s", count])
            return f"[LIVE DATA — {account} inbox]\n{out}"

    for pat, _ in CALENDAR_PATTERNS:
        if re.search(pat, msg):
            if "reminder" in msg:
                out = _run(["python3", HERMESCAL, "reminders"])
            else:
                out = _run(["python3", HERMESCAL, "events", "7"])
            return f"[LIVE DATA — calendar/reminders]\n{out}"

    return None

# ---------------------------------------------------------------------------

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

def inject_into_messages(messages: list) -> list:
    """Inject live data as a pre-executed tool result before the last user message."""
    msgs = [dict(m) for m in messages]
    for i in range(len(msgs) - 1, -1, -1):
        if msgs[i].get("role") == "user":
            content = msgs[i].get("content", "") or ""
            if isinstance(content, list):
                text = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
            else:
                text = content
            data = inject_data(text)
            if data:
                # Insert as assistant tool call + tool result before user message
                # so model treats it as already-executed and just formats the response
                tool_id = f"call_{uuid.uuid4().hex[:8]}"
                msgs.insert(i, {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": data,
                })
                msgs.insert(i, {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": tool_id,
                        "type": "function",
                        "function": {"name": "terminal", "arguments": "{}"},
                    }],
                })
            break
    return msgs

@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models_openai():
    res = requests.get(f"{OLLAMA_URL}/api/tags").json()
    models = [{"id": m["name"], "object": "model", "owned_by": "ollama"} for m in res.get("models", [])]
    return {"object": "list", "data": models}

@app.get("/api/tags", dependencies=[Depends(verify_api_key)])
async def list_models():
    return requests.get(f"{OLLAMA_URL}/api/tags").json()

class ChatRequest(BaseModel):
    model:       str  = DEFAULT_MODEL
    messages:    list
    stream:      bool = False
    tools:       list = []
    tool_choice: str  = "auto"

def stream_ollama(model: str, messages: list, ctx: str, tools: list = []):
    cid     = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    system, conv = build_ollama_messages(messages, ctx)
    payload = {
        "model": model, "messages": conv, "system": system,
        "stream": True, "options": OLLAMA_OPTIONS,
    }
    if tools:
        payload["tools"] = tools
    with requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True) as resp:
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            msg   = chunk.get("message", {})
            token = msg.get("content", "")
            done  = chunk.get("done", False)
            tool_calls = msg.get("tool_calls")
            delta = {"content": token}
            if tool_calls:
                delta["tool_calls"] = [
                    {
                        "index": i,
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": json.dumps(tc.get("function", {}).get("arguments", {})),
                        },
                    }
                    for i, tc in enumerate(tool_calls)
                ]
            sse = {
                "id": cid, "object": "chat.completion.chunk",
                "created": created, "model": model,
                "choices": [{"index": 0, "delta": delta,
                             "finish_reason": "tool_calls" if tool_calls else ("stop" if done else None)}],
            }
            yield f"data: {json.dumps(sse)}\n\n"
            if done:
                yield "data: [DONE]\n\n"
                return

@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat(request: ChatRequest):
    ctx = get_context()
    messages = inject_into_messages(request.messages)
    if request.stream:
        return StreamingResponse(
            stream_ollama(request.model, messages, ctx, request.tools),
            media_type="text/event-stream",
        )
    system, conv = build_ollama_messages(messages, ctx)
    payload = {
        "model": request.model, "messages": conv, "system": system,
        "stream": False, "options": OLLAMA_OPTIONS,
    }
    if request.tools:
        payload["tools"] = request.tools
    resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload)
    body = resp.json()
    msg  = body.get("message", {})
    content    = msg.get("content", "")
    tool_calls = msg.get("tool_calls")
    result_msg = {"role": "assistant", "content": content}
    if tool_calls:
        result_msg["tool_calls"] = [
            {
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": tc.get("function", {}).get("name", ""),
                    "arguments": json.dumps(tc.get("function", {}).get("arguments", {})),
                },
            }
            for tc in tool_calls
        ]
    finish = "tool_calls" if tool_calls else "stop"
    return {"choices": [{"message": result_msg, "finish_reason": finish}]}

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
