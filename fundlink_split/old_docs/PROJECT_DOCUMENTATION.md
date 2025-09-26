# FundLink Platform Documentation

_Last updated: 2025-02-14_

This document captures the current structure, behaviour, and integration points across the FundLink mono-repository. It focuses on the three core components—`fundlink_web`, `telbot_llm`, and `donation_verifier`—along with the shared tooling, background workers, and test suites. Use it as a reference when onboarding, planning refactors, or wiring new integrations.

---

## 1. High-Level Architecture

FundLink enables humanitarian donations on Avalanche Fuji via a Django REST API, Telegram bot, and on-chain verifier.

```
Telegram User       Donation Verifier            Avalanche Fuji RPC
     │                     │                               │
     │ 1. Message          │                               │
     ▼                     ▼                               ▼
┌──────────────┐   ┌────────────────────┐       ┌─────────────────┐
│ telbot_llm   │   │ donation_verifier  │       │ Avalanche Chain │
│ (Telegram    │   │ (async worker)     │       └─────────────────┘
│  service)    │   │                    │                ▲
└──────┬───────┘   └────────────┬───────┘                │ 3. poll
       │ 2. REST (internal key) │                        │
       ▼                       ▼                        │
┌────────────────────────────────────────────┐           │
│ fundlink_web (Django REST + Celery)        │◄──────────┘
│ - NGOs, Campaigns, Donations               │
│ - Internal bot & verifier endpoints        │
└────────────────────────────────────────────┘
```

- **Transport**: HTTP REST for service-to-service calls secured with `INTERNAL_API_KEY`. Telegram Bot uses polling (current) with planned webhook support.
- **Persistence**: Django uses SQLite in dev, PostgreSQL in prod; donation verifier maintains local JSON state between runs.
- **Background jobs**: Celery (planned) with Redis broker; donation verifier is a standalone async loop today.

---

## 2. Repository Layout

```
fundlink/
├── fundlink_web/                # Django project (core API)
│   ├── fundlink_backend/        # Settings, celery (planned), URLs
│   ├── donations/               # Donations domain app
│   ├── ngos/, campaigns/, ...   # Additional domain apps
│   ├── bot_integration/         # REST glue for Telegram bot
│   ├── bot_manager/             # Management command to run bot
│   └── requirements*.txt
├── telbot_llm/                  # Telegram bot + LLM orchestration
│   ├── bot/                     # Telegram entrypoint & handlers
│   ├── telbot_llm/              # Core logic, LLM interaction
│   ├── tests/                   # Pytest unit tests
│   └── run_bot.py               # Convenience launcher
├── donation_verifier/           # On-chain donation verifier
│   ├── config.py                # Environment loader
│   └── (other modules TBD)
├── requirements-all.txt         # Aggregate dependencies
├── decoupling_guide.md          # Service split roadmap
└── PROJECT_DOCUMENTATION.md     # (this file)
```

---

## 3. Dependency Overview

| Area            | Key Libraries                                                                                     |
|-----------------|----------------------------------------------------------------------------------------------------|
| Django backend  | Django 5.2, DRF, SimpleJWT, Celery, Redis client, psycopg, python-dotenv                           |
| Telegram bot    | python-telegram-bot 21.x, httpx, Pydantic, web3, python-dotenv                                     |
| LLM integration | Together API client (placeholder `together` package), custom `telbot_llm.llm_client` wrapper      |
| Tests & QA      | pytest, mypy, black, flake8                                                                        |

Ensure Python ≥3.11 (telegram bot code references 3.11-compatible features).

---

## 4. Environment & Configuration

- `.env` at repo root is loaded by both Django settings and the bot router. Critical variables include:
  - `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
  - `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
  - `REDIS_URL`
  - `INTERNAL_API_KEY` (shared secret for service-to-service auth)
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`
  - `AVALANCHE_RPC_URL`, `AVALANCHE_CHAIN_ID`, `USDT_CONTRACT_ADDRESS`
  - `TOGETHER_API_KEY` (LLM)
- Donation verifier (`donation_verifier/config.py`) expects `FUJI_RPC_URL` and `INTERNAL_API_KEY` at minimum.

---

## 5. Project: `telbot_llm`

### 5.1 Purpose
Implements the FundLink Telegram bot, including intent classification, response generation via LLM, and backend integrations.

### 5.2 Entry Points & CLI
- `run_bot.py`: loads `.env` and launches `bot.main.run_polling()`.
- Django managed command (in `fundlink_web/bot_manager`) imports `telbot_llm.bot.main` to run within Django context.

### 5.3 Key Modules & Functions

#### `bot/main.py`
- `build()` → configures `python-telegram-bot` `Application` with handlers.
- `run_polling(drop_pending=False)` → start polling mode.
- `run_webhook(webhook_url, listen, port, secret_token)` → start webhook-based bot.

#### `bot/handlers/chat.py`
- `start(update, context)` → replies with welcome copy.
- `chat(update, context)` → passes message to core handler with typing indicator.
- `handle_callback(update, context)` → delegates button callbacks to response agent.

#### `telbot_llm/handlers.py`
Maintains in-memory conversation state and bridges Telegram updates with intent/response agents.

- `get_user_state(telegram_id)` → retrieve or initialise mutable conversation state dict.
- `clear_ephemeral_state(telegram_id)` → reset conversation-specific fields after completion.
- `extract_amount_from_text(text)` / `extract_campaign_from_text(text, campaigns)` → heuristics for parsing user input.
- `handle_message(update, context)` → classify intent, call response agent, manage errors, telemetry.
- `handle_callback_query(update, context)` → decode button payloads and handle responses.
- `_ensure_user_registered(...)` → upsert bot user via backend internal API.
- `_reply_with_agent_messages(sender, response)` / `_edit_or_send(query, response)` → render `AgentResponse` objects into Telegram messages.

#### `telbot_llm/intent_agent.py`
Responsible for turning raw user text into structured intents.

- `IntentPrediction` dataclass → holds final prediction and raw response.
- `_normalise_entities(payload)` → sanitises LLM-provided entities.
- `_intent_from_raw(data)` → validates intent label, enforces confidence threshold.
- `classify_intent(user_text, user_state=None)` → orchestrates prompt, few-shot context, LLM call via `llm_client.complete`.

#### `telbot_llm/response_agent.py`
Deterministic layer mapping intents/entities to Telegram UI artefacts.

- Dataclasses: `ButtonSpec`, `AgentMessage`, `AgentResponse`.
- Core dispatcher: `handle_intent(intent, entities, telegram_id, user_state)`.
- Flow functions:
  - `view_campaigns(user_state)`
  - `select_campaign(user_state, campaign_id=None, campaign_title=None, detail_requested=False)`
  - `donate_flow(user_state, entities, telegram_id)`
  - `show_history(telegram_id)`
  - `confirm_donation(telegram_id, user_state)`
  - `help_menu(user_state)`, `unknown_menu(user_state)`, `bot_info(user_state)`, `out_of_scope(user_state)`, `metamask_help(user_state)`
- Callback processing: `handle_callback(action, payload, telegram_id, user_state)`
- Backend accessors: `_fetch_campaigns()`, `_fetch_campaign(campaign_id)`, `_resolve_campaign_by_title(title, user_state)`, `_campaign_from_entities(...)`
- Utilities: `_prepare_description(text)`, `_validate_token(token, campaign)`, `_amount_buttons(campaign, token)`, `_donation_metamask_link(...)`.

#### `telbot_llm/dialogue_renderer.py`
- `GeneratedMessage` dataclass.
- `generate_message(event, payload, user_state=None)` → wraps Together LLM to produce conversational copy, with fallback strings.

#### `telbot_llm/deep_link.py`
- `make_metamask_deep_link(address, amount, token=None, decimals=None)` → returns dict containing deep-link metadata.

#### `telbot_llm/router.py`
- `call_django_api(tool_name, params)` → asynchronous httpx client for backend endpoints (campaigns, donations, register_user, etc.).
- `_check(resp)` → raise `BackendAPIError` on non-2xx responses.

#### `telbot_llm/tools.py`
- `TOOLS` → OpenAI/Together function-call schema for backend integrations (list campaigns, register user, notify donor, etc.).

#### `telbot_llm/llm_client.py`
(Inspect to confirm behaviour.)
- Typically houses `complete(messages)` coroutine returning raw JSON string from Together API; handles retries and error translation to `LLMError`.

### 5.4 Tests
- `tests/test_intent_agent.py` → covers `classify_intent` fallback logic.
- `tests/test_response_agent.py` (if present) → ensures deterministic flows produce expected button layouts.
- Use `pytest` from repo root or inside `telbot_llm/`.

### 5.5 External Services
- Calls FundLink backend at `BACKEND_URL` (defaults to `http://localhost:8000`).
- Expects `INTERNAL_API_KEY` for secured endpoints.
- Relies on Together API (`TOGETHER_API_KEY`) for intent & dialogue generation.

---

## 6. Project: `fundlink_web`

### 6.1 Purpose
Primary Django REST API managing NGOs, campaigns, donations, and bot integration endpoints. Provides admin interface and handles donation lifecycle.

### 6.2 Settings & Configuration
- `fundlink_backend/settings.py` loads `.env`, configures apps, middlewares, database, static/media paths, JWT auth, CORS, Avalanche parameters, Celery placeholders.
- Environment-specific behaviour via `decouple.config` defaults.

### 6.3 URL Routing
- `fundlink_backend/urls.py` includes app routers for `campaigns`, `donations`, `ngos`, and `bot_integration` endpoints.

### 6.4 Domain Apps & Notable Components

#### `donations`
- **Models** (`models.py`): `Donation`, `DonationIntent`, `BotUser` etc.
- **Serializers** (`serializers.py`): `DonationSerializer`, `DonorHistorySerializer`, `BotUserSerializer`, `DonationIntentSerializer`.
- **Views** (`views.py`):
  - `DonationViewSet` (ReadOnlyModelViewSet) – filters confirmed donations, optional filters by telegram_id/NGO.
  - `donor_history(request)` – returns aggregated donation history.
  - `_is_internal_request(request)` – checks `Authorization`/`X-INTERNAL-KEY` against `INTERNAL_API_KEY`.
  - `_upsert_bot_user(...)` – syncs Telegram user metadata.
  - `create_donation_intent(request)` – internal API for bot to register expected donations; validates payload, persists intent, returns reference & expiry.
  - `list_donation_intents(request)` – internal listing (requires internal auth).
  - `claim_donation_intent(request, reference)` – marks intent as claimed once blockchain confirmation arrives.
  - `notify_donation(request)` – webhooks from verifier to notify donors.

- **Tests** (`tests/test_donation_intents.py`): cover intent creation, validation, security.

#### `ngos`, `campaigns`, `main`, `bot_integration`
- `bot_integration/views.py`:
  - `bot_notify(request)` – secured endpoint for donation verifier to enqueue Telegram notifications.
  - `register_user(request)` – internal bot user registration (supports alt header `X-INTERNAL-KEY`).
  - `user_exists(request)` – presence check.
  - `webhook_telegram(request)` – proxies incoming webhook to `telbot_llm` when running inside Django.
  - `health_check(request)` – simple service heartbeat.
- `bot_manager/management/commands/run_llm_bot.py`:
  - CLI for running Telegram bot (polling or webhook) inside Django environment with signal handling and environment validation.

### 6.5 Admin & Auth
- SimpleJWT configured in settings; `rest_framework` default permission `IsAuthenticated` except endpoints manually allowing `AllowAny`.
- Admin site for managing NGOs/campaigns/donations via standard Django admin.

### 6.6 Background Tasks
- Celery scaffolding planned (see documentation); `REDIS_URL` configured. No `celery_app.py` yet but guide suggests adding.

### 6.7 Static & Templates
- `static/`, `templates/` directories used by `main` app for web pages.

### 6.8 Tests
Run `python manage.py test` or targeted pytest modules (`fundlink_web/donations/tests/test_donation_intents.py`).

---

## 7. Project: `donation_verifier`

### 7.1 Purpose
External worker that watches Avalanche Fuji transactions, correlates them against registered donation intents, and notifies backend.

### 7.2 Core Module
- `config.py`
  - `VerifierSettings` dataclass encapsulating RPC, backend URLs, polling cadence, chain metadata, and state persistence file.
  - `VerifierSettings.load()` loads `.env`, validates required keys (`FUJI_RPC_URL`, `INTERNAL_API_KEY`), applies defaults.
- (Additional modules not included in snippet likely implement block polling, signature verification, and REST callbacks.)

### 7.3 Behaviour
- Polls Avalanche RPC (`rpc_url`) using `web3` settings defined elsewhere.
- Batch size/poll interval configurable via env.
- Persists progress (last block scanned) to JSON (`VERIFIER_STATE_PATH`).
- Posts confirmed donations to `fundlink_web` internal endpoints with `INTERNAL_API_KEY`.

---

## 8. Scripts & Tooling

- `run_bot.py` – convenience script to start Telegram bot in polling mode.
- `fundlink_web/setup.sh` – sets up virtualenv, installs requirements.
- `fundlink_web/manage.py` – Django CLI: migrations, createsuperuser, runserver.
- `telbot_llm/Makefile` – likely includes lint/test shortcuts (inspect for details).
- Pytest entrypoints: `pytest` in repo root honours `pytest.ini`.

---

## 9. Testing Strategy

- **Unit tests**: primarily in `telbot_llm/tests` and `fundlink_web/donations/tests`.
- **Integration tests**: Minimal currently; future work to add cross-service tests as part of decoupling.
- **Type checks**: `mypy.ini` targets `telbot_llm` modules.
- **Style**: `black`, `flake8` pinned versions in requirements for reproducible linting.

Command examples:
```bash
# Run Django tests
cd fundlink_web
python manage.py test

# Run bot tests
cd telbot_llm
pytest

# Type check
mypy telbot_llm
```

---

## 10. API Surface (Selected)

### Public / Semi-public
- `GET /api/campaigns/` – list active campaigns (supports filters).
- `GET /api/campaigns/{id}/` – campaign detail.
- `GET /api/donations/?telegram_id=` – donor history.
- `POST /api/ngos/apply/` – NGO application submission.

### Internal (secured via `INTERNAL_API_KEY`)
- `POST /api/bot/register-user/` – upsert Telegram user profile.
- `GET /api/bot/user-exists/?telegram_id=` – existence check.
- `POST /api/donations/intents/` – register expected donation.
- `POST /api/bot/notify/` – log/queue donor notification (currently stubbed).
- `POST /api/donations/notify/` – presumably used by donation verifier (check module).

Ensure headers: `Authorization: Bearer <INTERNAL_API_KEY>` or `X-INTERNAL-KEY` fallback.

---

## 11. Data Models Snapshot (donations app)

| Model          | Purpose                                                                                         |
|----------------|-------------------------------------------------------------------------------------------------|
| `Donation`     | Represents confirmed on-chain donation; tracks token, amount, status, tx hash, donor id.        |
| `DonationIntent` | Anticipated donation registered by bot; includes expiry, wallet address, token decimals.     |
| `BotUser`      | Telegram user metadata (id, username, names) used for notifications/history.                   |

Refer to `fundlink_web/donations/models.py` for field definitions and constraints.

---

## 12. Logging & Telemetry

- `telbot_llm` uses Python logging (`logging.basicConfig(level=logging.INFO)`) and optional metrics via `telbot_llm.telemetry.metrics` (exposed when available).
- Django leverages default logging; extend via settings for production.
- Donation verifier logs according to `VerifierSettings.log_level`.

---

## 13. Deployment Notes

- **Local development**: Use virtualenv, run Django server (`python manage.py runserver`), start bot via `python run_bot.py` with `.env` configured.
- **Production (current)**: Manual processes; see `README.md` inside `fundlink_web` for instructions on migrations, collectstatic, and Celery.
- **Planned**: Containerisation via Docker (see `decoupling_guide.md`), separate services for bot and web, Redis broker for Celery.

Checklist before deployment:
1. Ensure `.env` contains production secrets and `DEBUG=False`.
2. Run migrations (`python manage.py migrate`).
3. Collect static assets (`python manage.py collectstatic`).
4. Start web server via Gunicorn/UWSGI, behind Nginx.
5. Launch Telegram bot process (polling or webhook) with environment variables.
6. Run donation verifier with RPC credentials and internal API key.

---

## 14. Future Work References

- `decoupling_guide.md` – outlines migration to separate services, Redis-backed Celery workers, and Redis job scheduling.
- Telemetry enhancements, webhook-first bot deployment, and Celery worker improvements remain TODOs.

---

## 15. Quick Reference Tables

### 15.1 Core Functions by Component

| Component             | Function / Method                     | Summary                                                                  |
|-----------------------|---------------------------------------|--------------------------------------------------------------------------|
| `bot/main.py`         | `build()`                             | Configure Telegram application with handlers.                            |
|                       | `run_polling(drop_pending)`           | Launch bot in polling mode.                                              |
|                       | `run_webhook(url, listen, port, token)` | Launch bot in webhook mode.                                             |
| `bot/handlers/chat.py`| `start`                               | Welcome copy for `/start`.                                               |
|                       | `chat`                                | Delegates text messages to main handler.                                 |
|                       | `handle_callback`                     | Passes button callbacks to response agent.                               |
| `telbot_llm/handlers.py` | `handle_message`                  | Classify, route, and respond to messages.                                |
|                       | `handle_callback_query`               | Handle inline keyboard callbacks.                                        |
|                       | `get_user_state`                      | Retrieve per-user mutable state.                                         |
|                       | `clear_ephemeral_state`               | Reset state after flow completion.                                       |
|                       | `_ensure_user_registered`             | Upsert Telegram user via backend API.                                    |
| `telbot_llm/intent_agent.py` | `classify_intent`              | LLM-based intent classification with heuristics.                         |
| `telbot_llm/response_agent.py` | `handle_intent`             | Dispatch to flow-specific handlers.                                      |
|                       | `view_campaigns`                      | Fetch and render campaign list.                                          |
|                       | `select_campaign`                     | Set current campaign and prompt for detail/amount.                       |
|                       | `donate_flow`                         | Validate amount/token and produce donation prompt.                       |
|                       | `show_history`                        | Retrieve donor history via backend.                                      |
|                       | `confirm_donation`                    | Confirm donation receipt using backend checks.                           |
|                       | `help_menu` / `bot_info` / `metamask_help` | Provide support messaging.                                           |
|                       | `handle_callback`                     | Process button actions (select, donate, history).                         |
| `telbot_llm/dialogue_renderer.py` | `generate_message`       | Produce conversational copy via LLM fallback.                            |
| `telbot_llm/deep_link.py` | `make_metamask_deep_link`        | Build MetaMask donation link metadata.                                   |
| `telbot_llm/router.py` | `call_django_api`                   | REST client for backend tools.                                           |
| `fundlink_web/donations/views.py` | `DonationViewSet.get_queryset` | Filter confirmed donations, handle query params.                     |
|                       | `donor_history`                       | Aggregate donation history output.                                       |
|                       | `_is_internal_request`                | Validate internal auth headers.                                          |
|                       | `_upsert_bot_user`                    | Maintain `BotUser` records.                                              |
|                       | `create_donation_intent`              | Register donation intent from bot.                                       |
|                       | `list_donation_intents`               | Internal listing for verifier/bot.                                       |
|                       | `claim_donation_intent`               | Transition intent to claimed status on confirmation.                     |
| `fundlink_web/bot_integration/views.py` | `bot_notify`       | Log bot notifications (stub).                                            |
|                       | `register_user`                       | Internal registration endpoint.                                          |
|                       | `user_exists`                         | Existence check for Telegram ID.                                         |
|                       | `webhook_telegram`                    | Proxy Telegram webhook into `telbot_llm`.                                |
|                       | `health_check`                        | Service status endpoint.                                                 |
| `bot_manager/management/commands/run_llm_bot.py` | `Command.handle` | CLI entrypoint for polling/webhook bot.                           |
| `donation_verifier/config.py` | `VerifierSettings.load`      | Load verifier configuration from environment.                            |

---

## 16. Getting Started Quick Steps

1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements-all.txt`
3. Copy `.env.example` → `.env`, fill in secrets (Telegram token, internal API key, RPC URL).
4. `cd fundlink_web && python manage.py migrate && python manage.py runserver`
5. In new terminal: `cd telbot_llm && python run_bot.py`
6. (Optional) Start donation verifier once RPC + internal API are configured.

You're ready to iterate. Refer back to module sections for detailed behaviour when modifying flows or adding new endpoints.

---

_Questions or updates? Add comments inline and bump the “Last updated” stamp when you revise behaviour._
