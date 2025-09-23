# Fundlink Telegram Bot + Backend (SQLite) Guide

This document gives you an end-to-end procedure to run, interact with, and test the Fundlink Django backend + Telegram bot locally using SQLite (no Postgres required). It also covers webhook setup, donation simulation, deep links, and troubleshooting.

---
## 1. Architecture Snapshot
- **Django Backend** (`fundlink_web/`): NGOs, Campaigns, Donations, internal bot endpoints.
- **Telegram Bot** (`telbot_llm/` LLM-enhanced implementation).
- **Donation Verifier** (future/optional worker watching Fuji chain; can be simulated via internal notify endpoint).
- **Database**: SQLite file `fundlink_web/db.sqlite3` (already present / auto-created).

---
## 2. Project Structure
High-level relevant directories (trimmed to essentials):
```
fundlink/
├── bot.md                         # This guide
├── avalanche_fuji_donations_mvp_plan.md
├── telbot_llm_integration_plan.md
├── fundlink_web/                  # Django project root
│   ├── manage.py
│   ├── fundlink_backend/          # Django settings & root urls
│   ├── bot_integration/           # Bot-facing endpoints (notify, webhook, health)
│   ├── bot_manager/               # Django integration for LLM bot
│   │   └── management/
│   │       └── commands/
│   │           └── run_llm_bot.py # Management command to run LLM bot
│   ├── campaigns/                 # Campaign app (models, serializers, views)
│   ├── donations/                 # Donation records
│   ├── ngos/                      # NGO registration & data
│   ├── main/                      # (General pages / site shell)
│   ├── templates/                 # Django templates
│   ├── static/                    # Static assets
│   └── db.sqlite3                 # SQLite DB (dev)
├── archives/                      # Archived code
│   └── tel_bot/                   # (Archived) Classic Telegram bot implementation
├── telbot_llm/                    # LLM-enhanced bot implementation
│   ├── bot/                       # Telegram bot implementation
│   │   ├── handlers/              # Message handlers
│   │   └── main.py                # Bot application builder
│   ├── telbot_llm/                # Package code (handlers, router, tools)
│   │   ├── llm_client.py          # LLM API interaction
│   │   └── tools.py               # Tools for LLM to use
│   └── scripts/                   # Dev run & seeding scripts
├── donation_verifier/             # (Placeholder) future on-chain watcher
├── requirements-all.txt           # Aggregated dependencies (if used)
├── pytest.ini                     # Pytest configuration
└── .env / .env.example            # Environment variables (do not commit secrets)
```
Legend:
- Back-end API endpoints consumed by the bot live under `fundlink_web/bot_integration`.
- To add new campaign logic: modify `campaigns/` app and expose via DRF viewsets/endpoints.
- To extend bot commands: add a handler in `telbot_llm/telbot_llm/handlers.py` and wire it into router/dispatcher code.
- Future verifier should post to `bot_integration/notify/` with `X-INTERNAL-KEY`.

---
## 3. Prerequisites
- Python 3.11+ (confirm with `python --version`).
- A Telegram Bot token from BotFather.
- Optional: `ngrok` (or Cloudflare Tunnel / localhost.run) for webhook exposure.

---
## 4. TL;DR Quick Start
```bash
# From repo root
python -m venv .venv
source .venv/bin/activate
pip install -r fundlink_web/requirements.txt
pip install -r telbot_llm/requirements.txt

cp example.env .env  # (or create manually, see section 5)
# Edit TELEGRAM_BOT_TOKEN + INTERNAL_API_KEY + TOGETHER_API_KEY

# Run migrations
cd fundlink_web
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```
In a second terminal:
```bash
# (optional) expose backend
ngrok http 8000  # copy https URL

# Run LLM bot via Django
cd fundlink_web
python manage.py run_llm_bot --polling
```
Set webhook (replace TOKEN + URL):
```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=$PUBLIC_WEBHOOK_BASE/bot_integration/webhook/telegram/"
```
Start chatting with your bot in Telegram (`/start`).

---
## 5. Environment Variables (SQLite Friendly)
Create a root `.env` (or separate ones per component) with at least:
```env
DJANGO_SETTINGS_MODULE=fundlink_web.fundlink_backend.settings
DEBUG=1
SECRET_KEY=dev-insecure-secret
ALLOWED_HOSTS=localhost,127.0.0.1,ngrok-free.app
# Internal auth for bot notify endpoint
INTERNAL_API_KEY=your_internal_service_key
# Telegram
TELEGRAM_BOT_TOKEN=PUT_YOUR_BOTFATHER_TOKEN
PUBLIC_WEBHOOK_BASE=https://YOUR_NGROK_SUBDOMAIN.ngrok-free.app
# Optional LLM integration
TOGETHER_API_KEY=YOUR_OPTIONAL_KEY
TOGETHER_MODEL=meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8
LLM_TEMPERATURE=0.2
# Chain related (optional now; used by verifier)
AVALANCHE_RPC=https://api.avax-test.network/ext/bc/C/rpc
USDT_CONTRACT=0x5425890298aed601595a70AB815c96711a31Bc65
SNOWTRACE_BASE=https://testnet.snowtrace.io
```
SQLite does not require host/user/password variables—Django default config in `settings.py` already points to a local `db.sqlite3`.

If you keep separate env files (e.g. `tel_bot/.env`), repeat relevant keys (TOKEN, BACKEND_URL, INTERNAL_API_KEY).

---
## 6. Dependency Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r fundlink_web/requirements.txt
pip install -r telbot_llm/requirements.txt
```
(If you plan to run tests: also install `pytest`, `pytest-django` if not already in requirements.)

---
## 7. Database Setup (SQLite)
```bash
cd fundlink_web
python manage.py migrate
python manage.py createsuperuser  # create admin user for Django admin
```
To reset the DB:
```bash
rm db.sqlite3
python manage.py migrate
```

---
## 8. Running the Backend
```bash
cd fundlink_web
python manage.py runserver 0.0.0.0:8000
```
Visit:
- Admin: http://localhost:8000/admin/
- Health: http://localhost:8000/bot_integration/health/

---
## 9. Running the Telegram Bot
There are two main ways to run the LLM-enhanced bot:

### 9.1 Running the LLM Bot via Django (Recommended)
If you've set up the Django integration with the `bot_manager` app:

```bash
# Make sure you're in the fundlink_web directory
cd fundlink_web

# Run in polling mode (ideal for development)
python manage.py run_llm_bot --polling

# Run with webhook mode (production-ready)
python manage.py run_llm_bot
```

This approach has several advantages:
- Shares Django's environment and settings
- Proper signal handling for clean shutdowns
- Integrated logging with Django
- Access to Django's ORM if needed for advanced integrations
- Can be run as a proper service/daemon in production

---
## 10. Exposing Webhook (ngrok Example)
```bash
ngrok http 8000
```
Take the `https://<sub>.ngrok-free.app` URL and set `PUBLIC_WEBHOOK_BASE` accordingly, then:
```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=$PUBLIC_WEBHOOK_BASE/bot_integration/webhook/telegram/"
```
Check:
```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"
```
Clear webhook (switch to polling, if you add a polling mode):
```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/deleteWebhook"
```

---
## 11. Creating NGOs & Campaigns
1. Login to admin at `/admin/`.
2. Create an NGO with a valid Avalanche Fuji wallet (checksummed, e.g. `0x...`).
3. Create a Campaign linked to the NGO. (If there is an approval/publish flag in models, set it accordingly.)
4. Confirm via API (if endpoint exists) like: `GET /api/campaigns/`.

---
## 12. Deep Link Generation (MetaMask)
AVAX transaction deep link pattern:
```
https://metamask.app.link/send/<NGO_WALLET>?value=<WEI_AMOUNT>
```
Example: 0.25 AVAX (= 0.25 * 1e18 = 250000000000000000 wei)
```
https://metamask.app.link/send/0xABCDEF0123456789...?value=250000000000000000
```
You may later centralize logic (see `tel_bot/services/deep_link.py` or similar if present).

---
## 13. Simulating a Donation (Internal Notify)
Until the on-chain verifier is active, simulate detection:
```bash
curl -X POST http://localhost:8000/bot_integration/notify/ \
  -H "Content-Type: application/json" \
  -H "X-INTERNAL-KEY: $INTERNAL_API_KEY" \
  -d '{
    "tx_hash": "0xTESTHASH123",
    "amount_wei": "100000000000000000",  # 0.1 AVAX
    "wallet": "0xNGO_WALLET_ADDRESS",
    "sender": "0xDONOR_ADDRESS"
  }'
```
Expected: Django view records or acknowledges; Telegram bot (if coded to poll/receive internal triggers) sends a receipt message.

---
## 14. Testing (Optional)
Add a minimal smoke test file at `fundlink_web/tests/test_health.py`:
```python
import pytest
from django.urls import reverse

def test_health(client):
    resp = client.get('/bot_integration/health/')
    assert resp.status_code == 200
```
Run tests:
```bash
pytest -q
```
Specify Django settings (if not in `pytest.ini`):
```bash
DJANGO_SETTINGS_MODULE=fundlink_web.fundlink_backend.settings pytest -q
```

---
## 15. Useful Management Commands
```bash
# Django shell
python manage.py shell
# List routes (with django-extensions if installed)
python manage.py show_urls
# Dump data
python manage.py dumpdata > backup.json
# Load data
python manage.py loaddata backup.json
```

---
## 16. Resetting Everything (Hard Reset)
```bash
pkill -f runserver || true
rm fundlink_web/db.sqlite3
cd fundlink_web
python manage.py migrate
python manage.py createsuperuser
```
Re-seed NGOs/campaigns via admin or future seed script.

---
## 17. Security Notes
- Do NOT commit real `TELEGRAM_BOT_TOKEN` or `TOGETHER_API_KEY`.
- Rotate any leaked keys immediately.
- The `INTERNAL_API_KEY` header auth is minimal; consider HMAC with timestamp for production.
- Limit `ALLOWED_HOSTS` in non-dev environments.

---
## 18. Troubleshooting
| Symptom | Check |
|---------|-------|
| 403 on /bot_integration/notify/ | Missing or wrong `X-INTERNAL-KEY` header |
| Webhook not firing | `getWebhookInfo`, ngrok URL correctness, HTTPS only |
| Bot silent | Ensure bot process running & no exceptions in console |
| SQLite locked | Long-running shell holding transaction; restart server |
| ImportError | Re-activate venv, reinstall requirements |
| LLM Not Responding | Check TOGETHER_API_KEY, network connectivity |

Inspect Django logs (if configured) or run server with higher verbosity:
```bash
python manage.py runserver --verbosity 2
```

---
## 19. Optional: Integrating Verifier Later
When implementing the on-chain watcher:
1. Use `web3.py` with Fuji RPC (`AVALANCHE_RPC`).
2. Poll latest blocks or use websocket (if available) for transfers to NGO wallets.
3. On match, POST same JSON structure to `/bot_integration/notify/` with internal key.
4. Attach Snowtrace link: `https://testnet.snowtrace.io/tx/<tx_hash>`.

---
## 20. Using LLM-Powered Bot
The LLM-powered variant (`telbot_llm`) provides conversational interactions with context-aware responses:

### 20.1 Features
- Campaign browsing through natural language
- Donation deep link generation based on conversation
- Contextual memory of user interactions
- Fallback to basic response if LLM unavailable

### 20.2 How It Works
1. User sends a message to the bot
2. Bot fetches active campaigns from the Django backend
3. Context and history are passed to LLM (Together API)
4. LLM generates a response with campaign info
5. If donation intent is detected, deep links are added

### 20.3 LLM Bot Flow Example
```
User: "Hi"
Bot: "Welcome! I'm the Fundlink donation assistant. How can I help you today?"

User: "What campaigns are available?"
Bot: [Fetches from API] "Currently, we have 3 active campaigns:
     [1] Hurricane Relief - raised 5.2/10 AVAX
     [2] Clean Water Initiative - raised 3.4/15 AVAX 
     [3] Education Fund - raised 1.1/5 AVAX"

User: "I want to donate to the Clean Water campaign"
Bot: "Great choice! The Clean Water Initiative aims to provide...
     
     Donate link (MetaMask): https://metamask.app.link/send/0x123...456"
```

### 20.4 Starting the LLM Bot
Django integration (recommended):
```bash
# From fundlink_web directory
python manage.py run_llm_bot --polling
```

Standalone (alternative):
```bash
cd telbot_llm
python -m bot.main
```

---
## 21. Next Steps / Enhancements
- Add seed script (`scripts/seed_demo_data.py`).
- Add richer campaign browsing commands in the bot.
- Implement donation verification worker.
- Add rate limiting & better auth for internal endpoints.
- Introduce Celery or APScheduler for background tasks.
- Add streaming responses to LLM bot.
- Implement function calling for more structured LLM tools.

---
## 21. Minimal Command Reference (Copy/Paste)
```bash
# 1. Environment
python -m venv .venv && source .venv/bin/activate

# 2. Install
pip install -r fundlink_web/requirements.txt
pip install -r tel_bot/requirements.txt

# 3. Migrate
cd fundlink_web
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000

# 4. Ngrok (second terminal)
ngrok http 8000

# 5. Webhook
export TELEGRAM_BOT_TOKEN=... ; export PUBLIC_WEBHOOK_BASE=... # set them
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=$PUBLIC_WEBHOOK_BASE/bot_integration/webhook/telegram/"

# 6. Bot (third terminal):
cd fundlink_web
python manage.py run_llm_bot --polling

# 7. Simulate donation
curl -X POST http://localhost:8000/bot_integration/notify/ \
  -H "Content-Type: application/json" \
  -H "X-INTERNAL-KEY: $INTERNAL_API_KEY" \
  -d '{"tx_hash":"0xTEST","amount_wei":"100000000000000000","wallet":"0xNGO","sender":"0xDONOR"}'
```

---
## 23. Production Deployment Notes
For production deployment, consider:

### 23.1 Supervisor Configuration (Example)
```ini
[program:fundlink_bot]
command=/path/to/venv/bin/python /path/to/fundlink/fundlink_web/manage.py run_llm_bot
directory=/path/to/fundlink
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/fundlink-bot.log
environment=
    DJANGO_SETTINGS_MODULE="fundlink_web.fundlink_backend.settings",
    TELEGRAM_BOT_TOKEN="your_token_here",
    TOGETHER_API_KEY="your_together_api_key",
    PUBLIC_WEBHOOK_BASE="https://your-domain.com"
```

### 23.2 Security Hardening
- Move all secrets to environment variables or secure vault
- Add rate limiting for all API endpoints
- Implement proper HMAC-based authentication for internal endpoints
- Set up monitoring and alerting for bot failures
- Configure proper SSL for all endpoints

---
## 24. Need More?
Add issues or ask for scripts (e.g., automatic campaign seeding, verifier skeleton). This file is a living reference—extend it as flows evolve.
