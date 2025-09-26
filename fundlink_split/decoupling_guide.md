# FundLink Bot Decoupling Guide

## Goals
- Turn the Telegram-facing logic into an independent Django service (`fundlink_bot`).
- Keep the existing platform API (`fundlink_web`) focused on NGOs, campaigns, donations, and verification.
- Use Redis as the shared Celery broker while isolating persistence in separate Postgres databases.
- Formalise HTTP contracts between the services so they can scale and deploy independently.

## Target Architecture
```
┌────────────────────┐    HTTPS    ┌────────────────────┐
│   Telegram API     │◄──────────►│   fundlink_bot      │
└────────────────────┘             │  Django + Celery    │
                                   │  Postgres (bot DB)  │
                                   │  Redis (broker)     │
                                   └────────▲───────────┘
                                            │ REST (Bearer auth)
                                            │
                                   ┌────────┴───────────┐
                                   │   fundlink_web     │
                                   │  Django + Celery   │
                                   │  Postgres (core DB)│
                                   │  Redis (broker)    │
                                   └────────────────────┘
```
- `common/` Python package holds shared DTOs, auth helpers, and HTTP clients.
- Each Django project has its own `requirements`, `.env`, migrations, and Celery workers.

## Repository Layout
```
fundlink/
  common/
    common/__init__.py
    common/contracts.py
    common/http.py
    pyproject.toml
  fundlink_web/
    fundlink_backend/
      __init__.py            # imports celery_app
      celery_app.py
      settings.py
    ...
  fundlink_bot/
    fundlink_bot/
      __init__.py            # imports celery_app
      celery_app.py
      settings.py
    telegram_gateway/
    bot_state/
    integrations/
    manage.py
    requirements.txt
  docker-compose.yml
  .env.web.example
  .env.bot.example
  .env.common
```

## Data Stores
- **Postgres (core)**: `fundlink_web` authoritative data (NGOs, campaigns, donations).
- **Postgres (bot)**: `fundlink_bot` data (Telegram users, intents, chat sessions, delivery logs).
- **Redis**: single Redis instance using separate logical DBs or queue names per service; acts as Celery broker and optional cache/locking layer.

## Shared Package (`common/`)
- Define dataclasses or Pydantic models for payloads (`BotUserPayload`, `DonationNotification`, etc.).
- Store signature helpers for bearer tokens/HMAC.
- Provide thin HTTP clients with retry/backoff tuned for intra-cluster calls.
- Version the contracts and add tests to guard against breaking changes.

## Environment & Configuration
- `fundlink_web` reads configuration from `.env.web`: database DSN, Redis URI, `INTERNAL_API_KEY`, webhook callback URLs.
- `fundlink_bot` reads from `.env.bot`: bot DB DSN, Redis URI, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_URL`, `WEB_API_BASE_URL`, `INTERNAL_API_KEY`.
- `.env.common` holds values shared during local development; never commit real secrets.

## Implementation Phases
1. **Scaffold `fundlink_bot`**
   - `django-admin startproject fundlink_bot` inside repo.
   - Add apps `telegram_gateway` (webhook endpoints, management commands), `bot_state` (models), `integrations` (HTTP clients to web API).
   - Copy and adapt logic from `fundlink_web/bot_integration` and `bot_manager/management/commands/run_llm_bot.py`.
   - Add `celery_app.py` mirroring the web project but with bot-specific queues.
2. **Introduce `common/` package**
   - Move shared payload definitions and auth helpers out of the web project.
   - Install the package in editable mode for both projects (`pip install -e ./common`).
3. **Refactor fundlink_web**
   - Replace direct `telbot_llm` imports with HTTP calls using `common.http` clients.
   - Remove `bot_integration` and `bot_manager` apps once the new service is functional.
   - Update DRF internal endpoints (`/api/internal/...`) to match new contract versioning.
4. **Bot Persistence**
   - Create migrations for bot user tables, intent logs, message ledger.
   - Configure Django connections to the bot Postgres DSN.
5. **Celery & Scheduling**
   - Configure `fundlink_web` Celery queues (`web.default`, `web.verifier`, `web.notifications`).
   - Configure `fundlink_bot` Celery queues (`bot.webhook`, `bot.followups`, `bot.analytics`).
   - Use Redis DB 0 for web queues, DB 1 for bot queues, or use queue-based routing.
   - Set up Celery beat in both projects (one for platform tasks, one for bot reminders) reusing Redis as the scheduler backend.
6. **HTTP Integration**
   - `fundlink_bot` fetches campaign/NGO data from `fundlink_web` (GET endpoints with bearer auth).
   - `fundlink_web` pushes donation events or user sync POSTs to `fundlink_bot` internal endpoints.
   - Implement exponential backoff with jitter (e.g., via `tenacity`) and surface metrics on retries/failures.
7. **Testing**
   - Unit tests per project plus contract tests in `common/`.
   - Integration tests that spin up both Django apps (pytest + docker-compose) verifying webhook flows, Celery tasks, and data persistence.
8. **Cleanup**
   - Remove unused bot code from `fundlink_web` after parity is verified.
   - Update documentation, READMEs, and CI workflows.

## Celery + Redis Details
- Broker URL format: `redis://:<password>@redis:6379/0` (web) and `/1` (bot) or share `/0` but segment with queue names.
- Configure `CELERY_TASK_DEFAULT_QUEUE`, `CELERY_TASK_ROUTES`, and `worker_prefetch_multiplier` per service.
- Enable Redis result backend only for workflows needing result storage; otherwise prefer `rpc://` or disable results for performance.
- Apply idempotency by using unique keys (donation hash, Telegram update ID) and Redis-based locks (`redlock` or `SET NX`) to prevent duplicate processing when workers scale horizontally.
- Celery beat: run one per project (`celery -A fundlink_web.celery_app beat`, `celery -A fundlink_bot.celery_app beat`). Store schedules in Redis or Postgres depending on durability requirements.

## Deployment Outline
- Extend `docker-compose.yml` with services: `web`, `web-celery`, `web-beat`, `bot`, `bot-celery`, `bot-beat`, `redis`, `postgres-web`, `postgres-bot`, optional `nginx` for TLS/webhook proxy.
- Build separate Docker images for each Django project. Use a common Python base (e.g., Python 3.11 slim) and install project-specific requirements.
- In Kubernetes, deploy separate Deployments + HorizontalPodAutoscalers per service and Celery worker type; use ConfigMaps/Secrets for env vars; configure `CronJobs` if Celery beat is replaced by cluster scheduling.
- Ensure readiness probes check `/healthz` endpoints; liveness probes can hit Celery worker heartbeat endpoints, e.g., `celery -A ... inspect ping` via sidecar script.
- For Telegram webhook registration: add a management command or startup script in `fundlink_bot` that calls `setWebhook` using `TELEGRAM_WEBHOOK_URL` and verifies the response.

## Migration Checklist
- [ ] Create `fundlink_bot` project with initial settings, requirements, Dockerfile.
- [ ] Stand up dedicated Postgres instance and apply initial migrations.
- [ ] Implement shared `common/` package and update both projects to use it.
- [ ] Port bot logic, tests, and Celery configuration to the new project.
- [ ] Replace direct integrations in `fundlink_web` with HTTP clients.
- [ ] Verify end-to-end bot flow (Telegram update ⇒ webhook ⇒ bot service ⇒ web API ⇒ DB updates).
- [ ] Run Celery workers/beat for both services; confirm scheduled tasks run via Redis.
- [ ] Update CI/CD pipelines to build/test/deploy both projects and publish images.
- [ ] Remove legacy bot apps, unused dependencies, and update documentation.

## Rollback Strategy
- Keep existing `bot_integration` endpoints until the new service is live; route traffic via feature flag or environment toggle.
- Deploy `fundlink_bot` in parallel and run shadow traffic tests; monitor logs and metrics before switching Telegram webhook to the new service.
- If issues arise, revert webhook to the old polling-based bot or re-enable legacy endpoints while investigating.

## Open Questions
- Do we need real-time streaming (webhooks back to bot) for donation events, or is polling the web API sufficient?
- Should Redis be shared with other infrastructure components (e.g., rate limiting) or kept exclusive to Celery?
- How will secrets be managed in production (Vault, AWS Secrets Manager, etc.)?
- What telemetry/alerting stack will watch Celery queue depth, HTTP error rates, and webhook failures?

Keep this guide alongside `telbot_llm_integration_plan.md` so future contributors understand the service boundaries and the rationale for the split.
