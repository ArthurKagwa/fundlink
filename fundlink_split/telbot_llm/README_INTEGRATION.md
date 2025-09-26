TelBot LLM Integration
=======================

Overview
--------
`telbot_llm` provides a thin tool-calling layer over Together AI models for the FundLink Telegram bot. It enables the model to request backend data (campaigns, donations, user registration, NGO application) rather than hallucinating blockchain / campaign facts.

Key Modules
-----------
- `llm_client.py`: Orchestrates chat calls with fallback model.
- `tools.py`: JSON schema definitions for allowed function calls.
- `router.py`: HTTP bridge to Django backend API.
- `handlers.py`: Telegram message handler integrating everything.
- `errors.py`: Typed exceptions.
- `telemetry/metrics.py`: Optional Prometheus counters.

Environment Vars
----------------
Required:
- `TOGETHER_API_KEY`
- `BACKEND_URL` (e.g. http://localhost:8000)
Optional:
- `INTERNAL_API_KEY` (secure internal endpoints)
- `TOGETHER_MODEL` (default 70B instruct)
- `TOGETHER_MODEL_FALLBACK` (default 8B instruct)
- `LLM_TEMPERATURE` (default 0.2)
- `HTTP_TIMEOUT` (default 20)
- `DISABLE_METRICS` (set=1 to turn off Prometheus objects)

Wire Into Telegram Bot
----------------------
```
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from telbot_llm.handlers import handle_message

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
```

Local Dev Quickstart
--------------------
```
export TOGETHER_API_KEY=sk_...
export BACKEND_URL=http://localhost:8000
pytest -q telbot_llm/tests
```

Design Notes
------------
1. The model never receives raw blockchain addresses unless sourced from a tool.
2. Tool arguments are validated by the backend; the LLM layer is untrusted.
3. Fallback model ensures degraded but functional service on primary failure.
4. Metrics are in-process only; push gateway / exposition can be added later.

Future Enhancements
-------------------
- Streaming partial tokens to Telegram.
- Redis caching for `list_campaigns`.
- Guardrails / JSON schema validation pre-flight.
