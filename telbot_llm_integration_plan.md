# FundLink Telegram LLM Integration Plan

This document describes how to integrate a tool-calling LLM module (`telbot_llm/`) into the existing FundLink humanitarian donations MVP. The goal is to enable conversational, intelligent interactions in Telegram while seamlessly connecting to the Django backend and donation verifier.

---

## 1. Objectives
- Add an LLM-powered layer inside the Telegram bot for natural language understanding.
- Expose Django REST endpoints as **tools** callable by the LLM.
- Ensure smooth integration with donation verification and donor notifications.
- Keep the system modular: LLM logic lives in `telbot_llm/`, not mixed into core bot command handlers.

---

## 2. System Architecture
```
Telegram User → Telegram Bot (python-telegram-bot)
                    │
                    ▼
             telbot_llm (LLM + Tools)
                    │
                    ▼
          Django Backend (REST API + DB)
                    │
                    ▼
       Donation Verifier (web3.py worker)
```

- **Telegram Bot:** Handles messages, passes them to `telbot_llm`.
- **LLM Engine:** Parses intent, decides whether to call tools.
- **Tool Layer:** Functions mapped to Django API endpoints.
- **Django Backend:** Responds with structured data (campaigns, donations, NGO info).
- **Verifier:** Triggers `notify_donor` → handled by bot with LLM phrasing.

---

## 3. Components

### 3.1 `telbot_llm/`
- **`llm_client.py`**: Wrapper for calling the LLM API (OpenAI/Together/etc.). Supports function/tool calling.
- **`tools.py`**: Defines schemas for each tool and how to call Django.
- **`router.py`**: Receives LLM tool calls, dispatches to Django API functions.
- **`handlers.py`**: High-level logic to integrate with `python-telegram-bot` message handlers.

### 3.2 Tools → Django Endpoints
| Tool Name        | Django Endpoint                   | Method | Purpose |
|------------------|-----------------------------------|--------|---------|
| `list_campaigns` | `/api/campaigns/`                | GET    | Fetch campaigns for browsing |
| `get_campaign`   | `/api/campaigns/{id}/`           | GET    | Campaign details |
| `register_user`  | `/api/bot/register-user/`        | POST   | Register Telegram user in DB |
| `get_donations`  | `/api/donations/`                | GET    | Fetch donation history |
| `notify_donor`   | `/api/bot/notify/`               | POST   | Send donor a notification |
| `apply_ngo`      | `/api/ngos/apply/`               | POST   | NGO registration |

### 3.3 Conversation Flow Example
1. **User:** "I want to donate 0.1 AVAX to flood relief."
2. **Bot → LLM:** LLM parses intent, triggers `list_campaigns` to identify flood campaign.
3. **LLM → Bot:** Returns deep link `https://metamask.app.link/send/...`.
4. **User:** Clicks, completes transaction.
5. **Verifier:** Detects tx, records donation, calls `notify_donor`.
6. **Bot:** Uses LLM to phrase natural receipt: "✅ 0.1 AVAX confirmed for Flood Relief XYZ. View on Snowtrace: <link>".

---

## 4. Technical Steps

### Step 1: Create `telbot_llm/`
```bash
mkdir telbot_llm
cd telbot_llm
touch __init__.py llm_client.py tools.py router.py handlers.py
```

### Step 2: Define Tool Schemas (`tools.py`)
```python
tools = [
    {
        "name": "list_campaigns",
        "description": "Get list of active campaigns",
        "parameters": {}
    },
    {
        "name": "get_donations",
        "description": "Get donation history for a Telegram user",
        "parameters": {"telegram_id": "string"}
    },
    # etc...
]
```

### Step 3: Implement Django API Calls (`router.py`)
```python
import httpx, os

BACKEND_URL = os.getenv("BACKEND_URL")
API_KEY = os.getenv("BACKEND_API_KEY")

async def call_django_api(tool_name, params):
    async with httpx.AsyncClient() as client:
        if tool_name == "list_campaigns":
            r = await client.get(f"{BACKEND_URL}/api/campaigns/")
            return r.json()
        elif tool_name == "get_donations":
            r = await client.get(f"{BACKEND_URL}/api/donations/", params=params)
            return r.json()
        elif tool_name == "notify_donor":
            r = await client.post(f"{BACKEND_URL}/api/bot/notify/", json=params, headers={"Authorization": f"Bearer {API_KEY}"})
            return r.json()
```

### Step 4: LLM Call (`llm_client.py`)
- Calls chosen LLM (OpenAI, Together).
- Provides conversation history + `tools` definitions.
- Handles tool_call vs text-only response.

### Step 5: Integrate into Bot (`handlers.py`)
```python
from telegram import Update
from telegram.ext import ContextTypes
from .llm_client import chat_with_tools
from .router import call_django_api

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    telegram_id = str(update.message.from_user.id)

    response = await chat_with_tools(user_text, telegram_id)

    if response.get("tool_call"):
        result = await call_django_api(response["tool_call"]["name"], response["tool_call"]["parameters"])
        final_answer = await response["continue_with"](result)
    else:
        final_answer = response["text"]

    await update.message.reply_text(final_answer)
```

### Step 6: Plug into Bot Runner
In `tel_bot/bot.py`:
```python
from telbot_llm.handlers import handle_message

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
```

---

## 5. Security & Validation
- **API Key**: All bot→Django calls use `BACKEND_API_KEY`.
- **Rate Limits**: Apply throttling on public endpoints.
- **Wallet Validation**: Django enforces checksum validation.
- **Safe Output**: LLM responses sanitized before sending.

---

## 6. Deployment Strategy
1. Update environment variables in `.env` for bot runner.
2. Deploy Django backend as usual (Railway/Render).
3. Deploy bot runner (Railway worker or VM with systemd).
4. Verify donation flows end-to-end with Fuji testnet faucet.

---

## 7. Testing Plan
- **Unit Tests:** Tool mapping, API responses, LLM fallback when tool fails.
- **Integration Tests:** Telegram → LLM → Django → Verifier → Receipt.
- **Edge Cases:** Invalid campaign ID, donation < min amount, duplicate tx.

---

## 8. Future Enhancements
- Support multi-turn memory (donor can say "same as last time").
- Add campaign search by natural query ("Show me flood campaigns").
- Support impact posts summarised by LLM.
- Deploy on mainnet with stablecoins.

---

**End of Plan**



---

## 9. Together.ai LLM Wiring
Use Together’s Responses API with **function tools** to give the LLM structured access to Django.

### 9.1 Models
Pick one primary model and one fallback. Reasonable defaults:
- `meta-llama/Llama-3.1-70B-Instruct-Turbo` (primary)
- `meta-llama/Llama-3.1-8B-Instruct` (fallback to save cost/latency)

> You can swap models without changing the rest of the integration.

### 9.2 Environment Variables
Add these to the bot runner env (e.g., `tel_bot/.env`):
```env
TOGETHER_API_KEY=xxxxxxxxxxxxxxxx
TOGETHER_MODEL=meta-llama/Llama-3.1-70B-Instruct-Turbo
LLM_TEMPERATURE=0.2
```

### 9.3 Python Client Setup (`telbot_llm/llm_client.py`)
```python
from together import Together
import os

MODEL = os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.1-70B-Instruct-Turbo")
TEMP = float(os.getenv("LLM_TEMPERATURE", 0.2))

def get_client():
    return Together(api_key=os.getenv("TOGETHER_API_KEY"))

# Base system prompt keeps the bot helpful but constrained to allowed tools
SYSTEM = (
    "You are FundLink's Telegram assistant. "
    "Answer concisely. When actions are required, call a provided tool. "
    "Never fabricate blockchain data; defer to tools for facts."
)

```

### 9.4 Tool Schemas for Together (`telbot_llm/tools.py`)
> Together uses OpenAI-style function tools. Define tools as JSON schema objects.
```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_campaigns",
            "description": "Get list of active campaigns.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_campaign",
            "description": "Get campaign detail by id.",
            "parameters": {
                "type": "object",
                "properties": {"campaign_id": {"type": "integer"}},
                "required": ["campaign_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_donations",
            "description": "Get donation history for a Telegram user.",
            "parameters": {
                "type": "object",
                "properties": {"telegram_id": {"type": "string"}},
                "required": ["telegram_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "register_user",
            "description": "Register a Telegram user in the backend.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_id": {"type": "string"},
                    "username": {"type": "string"}
                },
                "required": ["telegram_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_donor",
            "description": "Send a donor a message via backend (secured).",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_id": {"type": "string"},
                    "message": {"type": "string"}
                },
                "required": ["telegram_id", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_ngo",
            "description": "Submit NGO application payload.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "wallet_address": {"type": "string"},
                    "website": {"type": "string"}
                },
                "required": ["name", "email", "wallet_address"],
            },
        },
    },
]
```

### 9.5 Turn Handling (with Tool Calls) (`telbot_llm/llm_client.py`)
```python
from .tools import TOOLS

async def chat_with_tools(user_text: str, telegram_id: str, history: list[dict] | None = None):
    client = get_client()
    messages = [{"role": "system", "content": SYSTEM}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    # First turn: allow the model to request a tool
    resp = client.responses.create(
        model=MODEL,
        input=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=TEMP,
    )

    out = resp.output[0]  # Together responses are batched; use first item

    # If the model called a tool
    if hasattr(out, "tool_calls") and out.tool_calls:
        call = out.tool_calls[0]
        return {
            "tool_call": {"name": call.function.name, "arguments": call.function.arguments},
            "finish_reason": out.finish_reason,
            "messages": messages,
        }

    # Otherwise return the text
    return {"text": out.content[0].text, "messages": messages}

async def continue_with_tool_result(state: dict, tool_result: dict | list | str):
    client = get_client()
    messages = state["messages"] + [
        {"role": "tool", "content": str(tool_result)}
    ]
    resp = client.responses.create(
        model=MODEL,
        input=messages,
        temperature=TEMP,
    )
    out = resp.output[0]
    return out.content[0].text
```

### 9.6 Router to Django (`telbot_llm/router.py`)
```python
import os, httpx
BACKEND_URL = os.getenv("BACKEND_URL")
API_KEY = os.getenv("BACKEND_API_KEY")

async def call_django_api(name: str, args: dict):
    async with httpx.AsyncClient(timeout=20) as client:
        if name == "list_campaigns":
            r = await client.get(f"{BACKEND_URL}/api/campaigns/")
            return r.json()
        if name == "get_campaign":
            cid = args.get("campaign_id")
            r = await client.get(f"{BACKEND_URL}/api/campaigns/{cid}/")
            return r.json()
        if name == "get_donations":
            r = await client.get(f"{BACKEND_URL}/api/donations/", params=args)
            return r.json()
        if name == "register_user":
            r = await client.post(f"{BACKEND_URL}/api/bot/register-user/", json=args, headers={"Authorization": f"Bearer {API_KEY}"})
            return r.json()
        if name == "notify_donor":
            r = await client.post(f"{BACKEND_URL}/api/bot/notify/", json=args, headers={"Authorization": f"Bearer {API_KEY}"})
            return r.json()
        if name == "apply_ngo":
            r = await client.post(f"{BACKEND_URL}/api/ngos/apply/", json=args)
            return r.json()
        return {"error": f"Unknown tool {name}"}
```

### 9.7 Telegram Handler Glue (`telbot_llm/handlers.py`)
```python
from telegram import Update
from telegram.ext import ContextTypes
from .llm_client import chat_with_tools, continue_with_tool_result
from .router import call_django_api

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    tg_id = str(update.message.from_user.id)

    # Optional: register user silently
    try:
        await call_django_api("register_user", {"telegram_id": tg_id, "username": update.message.from_user.username or ""})
    except Exception:
        pass

    first = await chat_with_tools(text, tg_id)

    if first.get("tool_call"):
        tool = first["tool_call"]
        result = await call_django_api(tool["name"], tool["arguments"])
        final_text = await continue_with_tool_result(first, result)
    else:
        final_text = first["text"]

    await update.message.reply_text(final_text, disable_web_page_preview=True)
```

### 9.8 Streaming (Optional)
For faster perceived latency, stream tokens and intercept tool calls:
- Call `client.responses.stream.create(...)` and iterate events.
- If an event of `type == "tool_call"` arrives, pause stream, execute tool, then send a follow-up turn.

### 9.9 Safety & Guardrails
- **Tool-only for critical actions:** The model must not invent transaction hashes; it must call tools.
- **Regex/HTML sanitization:** Strip unwanted HTML before replying.
- **Rate limiting:** Per Telegram user and per endpoint to prevent abuse.
- **Time-boxing:** Cancel LLM requests that exceed 10–15s.

### 9.10 Observability
- Log: `prompt_tokens`, `completion_tokens`, `latency_ms`, chosen tool.
- Attach `x-request-id` to Django calls for traceability.
- Healthcheck pings for LLM and backend.

### 9.11 Cost/Latency Controls
- Route short queries to `8B` model; long/tool-heavy to `70B`.
- Lower temperature for deterministic tool selection.
- Cache `/api/campaigns/` results briefly (30–60s).

### 9.12 E2E Test Matrix
- Natural: "donate 10 USDT to flood relief" → tool path then deep link text.
- History: "what have I donated before?" → `get_donations` → summarized list.
- NGO: "register my NGO" → `apply_ngo` with collected fields.
- Errors: bad `campaign_id`, network timeout, backend 500 → graceful replies.

### 9.13 Deployment Notes
- Put `TOGETHER_API_KEY` only on the bot runner.
- Rollbacks: keep a non-LLM fallback handler for `/start`, `/help`, `/campaigns`.
- Blue/green deploy the bot worker to avoid dropped webhooks.

