# Copilot Instructions for AI Agents

## Project Overview
This project is a humanitarian donations MVP for Avalanche Fuji testnet. It integrates a Telegram bot, a Django backend (with DRF), and a web3.py-based donation verifier. The system enables donors to contribute AVAX or USDT to approved NGOs, with on-chain verification and impact tracking.

## Architecture & Key Components
- **Telegram Bot** (`python-telegram-bot`): Handles user interaction, campaign browsing, and donation deep link generation. Relies on backend for campaign data and donation receipts.
- **Django Web App** (DRF + Admin): Manages NGO registration, campaign CRUD, admin approvals, and impact posts. Exposes REST API endpoints for bot and verifier.
- **Donation Verifier** (`web3.py` worker): Monitors Avalanche Fuji C-Chain for AVAX transfers to NGO wallets. On match, records donation and triggers Telegram notification.
- **Postgres Database**: Stores NGOs, campaigns, donations, impact posts, and bot users.

## Developer Workflows
- **Processes:**
  - `web`: Django + DRF
  - `bot`: Telegram bot (webhook )
  - `verifier`: web3.py worker (Celery or long-running script)
- **Config:** All secrets and endpoints via environment variables (see plan for required keys).
- **Testing:**
  - Unit: serializers, viewsets, wallet validation
  - Integration: end-to-end bot → API → deep link → on-chain tx → verifier → receipt
- **Deployment:** Railway/Render/Fly.io for backend; managed Postgres; logs to stdout; error alerting via Sentry/Healthchecks.

## Project-Specific Patterns & Conventions
- **MetaMask Deep Links:**
  - AVAX: `https://metamask.app.link/send/0xNGOADDR?value=...`
- **Data Model:** See plan for full schema. Key: `Donation.tx_hash` unique, `NGO.wallet_address` unique and checksummed.
- **API Endpoints:**
  - `/api/campaigns/`, `/api/donations?telegram_id=...`, `/api/bot/notify` (secured)
  - Admin: `/api/admin/ngos/{id}/approve`, `/api/admin/campaigns/{id}/publish`
- **Security:**
  - JWT/Token auth for NGOs, Django Admin for staff, HMAC secrets for internal endpoints
  - Input validation and rate limiting on bot endpoints
- **Explorer Links:** Use Snowtrace testnet: `https://testnet.snowtrace.io/tx/{tx_hash}`

## Integration Points
- **Telegram Bot ↔ Backend:** REST API for campaigns, donations, and notifications
- **Verifier ↔ Backend:** Internal API call to `/api/bot/notify` to trigger Telegram receipts
- **Web3:** Use Fuji RPC: `https://api.avax-test.network/ext/bc/C/rpc`, USDT contract: `0x5425890298aed601595a70AB815c96711a31Bc65`

## References
- See `avalanche_fuji_donations_mvp_plan.md` for full architecture, data model, and flows.
- All new features should align with the MVP plan and data model.

---

**If you are unsure about a workflow or integration, consult the MVP plan or ask for clarification.**
