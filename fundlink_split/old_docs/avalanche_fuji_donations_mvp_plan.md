# FUNDLINK : Avalanche Fuji Humanitarian Donations MVP – Implementation Plan

## 1) Scope & Objectives
**Goal:** Ship a working proof‑of‑concept that lets a donor use a Telegram bot to donate AVAX or USDT (Fuji testnet) directly to an approved NGO wallet, with a Django web app for NGO registration, admin approvals, campaign publishing, and basic impact traceability.

**What’s in (MVP):**
- Telegram bot with conversational donation flow and MetaMask deep links.
- Django web app: NGO registration, Admin approval, Campaign CRUD, Impact posts.
- Donation verification service (web3.py) watching Fuji C‑Chain for native AVAX transfers and USDT `Transfer` events.
- Donor receipt in Telegram after on‑chain confirmation, plus a simple donor history page.

**What’s out (later phases):**
- Multi‑chain support, recurring donations, automated splits, custodial wallets, KYC/AML tooling, fiat on‑ramps.

---

## 2) High‑Level Architecture
```
Telegram User ──(chat)──> Telegram Bot (python-telegram-bot)
                                 │
                                 ▼
                         Django Backend (REST API)
                         • DRF: NGOs, Campaigns, Donations, Impact
                         • Admin: approvals, moderation
                                 │
                                 ▼
                    Donation Verifier (web3.py worker)
                    • Avalanche Fuji RPC
                    • Watch AVAX tx + USDT Transfer events
                                 │
                                 ▼
                            Postgres Database
                                 │
                                 ▼
                     Notifications back to Telegram Bot
```

---

## 3) Environments & Network
- **Chain:** Avalanche Fuji (C‑Chain)
  - RPC: `https://api.avax-test.network/ext/bc/C/rpc`
  - Chain ID: `43113`
  - Explorer: Snowtrace testnet
  - USDT (test token) contract: `0x5425890298aed601595a70AB815c96711a31Bc65` (6 decimals)
- **App hosting (suggested):**
  - Backend: Railway / Render / Fly.io
  - Postgres: Managed (Railway/Render/Neon)
  - Bot runner & web3 worker: same host as Django, separate processes or Celery workers

---

## 4) Core Components
### 4.1 Telegram Bot (python-telegram-bot)
- Commands: `/start`, `/donate`, `/campaigns`, `/history`
- Inline menus for active campaigns and donation amounts.
- Generates **MetaMask deep links**:
  - AVAX example (0.1 AVAX):
    `https://metamask.app.link/send/0xNGOADDR?value=100000000000000000`
  - USDT example (10 USDT):
    `https://metamask.app.link/send/0xNGOADDR?value=10000000&contractAddress=0x5425890298aed601595a70AB815c96711a31Bc65`
- After user clicks and pays, bot relies on backend callbacks to send receipts.

### 4.2 Django Web App (DRF + Admin)
- **Public:** NGO application form; campaign list; read‑only impact updates.
- **NGO portal:** Edit profile, submit campaigns, post impact.
- **Admin:** Approve NGOs; approve/retire campaigns; moderate impact posts.
- **API:** Endpoints consumed by the bot and the verifier.

### 4.3 Donation Verifier (web3.py worker)
- Subscribes/polls Fuji RPC for:
  - **Native AVAX transfers:** parse tx receipts; match `to == NGO wallet` and `value`.
  - **USDT ERC‑20:** filter `Transfer(address,address,uint256)` where `to == NGO wallet`.
- On match → create `Donation` record → trigger Telegram receipt via bot webhook/queue.

---

## 5) Data Model (initial)
```
NGO(id, name, email, wallet_address, website, docs_url, approved:bool, created_at)
Campaign(id, ngo_id→NGO, title, description, active:bool, token_options:['AVAX','USDT'], min_amount, created_at)
Donation(id, ngo_id→NGO, campaign_id→Campaign|null, token:'AVAX'|'USDT', amount_decimal, tx_hash, chain_id, donor_telegram_id, confirmed_at, created_at)
ImpactPost(id, campaign_id→Campaign, title, body, media_url, published:bool, created_at)
BotUser(id, telegram_id, username, last_seen_at)
```

**Indexes:**
- `Donation.tx_hash` unique.
- `Donation.ngo_id`, `Donation.campaign_id` for reporting.
- `NGO.wallet_address` unique (lowercased, checksum validated).

---

## 6) REST API (DRF)
- `GET /api/campaigns/` → list active, approved campaigns with NGO name and wallet.
- `GET /api/campaigns/{id}/` → detail.
- `POST /api/ngos/apply/` → application payload.
- `GET /api/donations?telegram_id=...` → donor history (for bot `/history`).
- `POST /api/bot/notify` (internal) → endpoint the verifier calls to request a Telegram message to a user (secured by token/secret).

**Admin‑only:**
- `POST /api/admin/ngos/{id}/approve`
- `POST /api/admin/campaigns/{id}/publish`

---

## 7) Telegram Conversation Flows
### 7.1 Start & Pick Campaign
1. User: `/start`
2. Bot: welcome + buttons: “View campaigns”, “My history”
3. User taps “View campaigns” → list of active campaigns
4. User selects a campaign → bot shows description, NGO name, choose amount (1, 5, 10, custom)

### 7.2 Generate Deep Link & Pay
5. User selects token (AVAX/USDT) and amount
6. Bot builds MetaMask deep link and returns InlineKeyboard button “Donate with MetaMask”
7. User taps → MetaMask opens → user confirms tx

### 7.3 Verify & Receipt
8. Verifier catches tx → stores `Donation`
9. Backend calls bot notify → Bot: “✅ Received 10 USDT for *Flood Relief XYZ*. Tx: <Snowtrace link>.”

### 7.4 Donor History
- `/history` → bot queries `GET /api/donations?telegram_id=...` and prints a compact list with dates and explorer links.

---

## 8) Validation & Security
- **Wallet address hygiene:** checksum verification; blocklist if required.
- **Auth:**
  - DRF JWT/Token for NGO log‑in.
  - Admin via Django Admin with 2FA (plugin) if available.
  - Internal secrets for `/api/bot/notify` and verifier → backend calls.
- **Rate limits:** throttle bot endpoints to deter scraping.
- **Input validation:** campaign titles/descriptions length, sanitise HTML in impact posts.
- **Webhooks:** verify origin via HMAC secret.

---

## 9) Donation Verifier – Logic Outline
**AVAX (native):**
- Poll latest blocks; for each tx to any `NGO.wallet_address`, check receipt `status==1`. Record `value` in AVAX (convert to decimal). Map to campaign if deep link contained a `campaign_id` param (optionally append `?ref=cid:123&amt=10&tok=AVAX` to Telegram button and log pre‑intent in DB).

**USDT (ERC‑20):**
- Subscribe/poll `Transfer` events from `USDT_CONTRACT` where `to in NGO_wallets`.
- Compute amount = `value / 10^6`.
- Store donation and trigger notify.

**Explorer Links:**
- Snowtrace testnet: `https://testnet.snowtrace.io/tx/{tx_hash}`

---

## 10) Deployment & Operations
- **Config via env:** RPC URL, USDT contract, chain id, bot token, API secrets.
- **Processes:**
  - `web`: Django + DRF
  - `bot`: python-telegram-bot app (webhook or polling)
  - `verifier`: web3.py worker (Celery beat/worker or simple long‑running script managed by Supervisor/Systemd)
- **Logs & Monitoring:**
  - Structured logs (JSON) to stdout
  - Error alerting (Sentry/Healthchecks)
  - DB backups scheduled daily

---

## 11) Testing Plan
- Unit tests: serializers, viewsets, wallet validation.
- Integration: bot → API → deep link → faucet‑funded MetaMask tx → verifier detects → receipt.
- Edge cases:
  - Wrong token/chain → ignored.
  - Duplicate tx hash → prevented by unique index.
  - Very small amounts → enforce `min_amount` per campaign.

---

## 12) Timeline (aggressive 1–2 weeks)
**Day 1–2:** Django project + models + DRF + Admin.  
**Day 3–4:** Telegram bot scaffolding + campaigns listing + deep link generation.  
**Day 5–6:** Verifier (AVAX + USDT) + notifications.  
**Day 7:** NGO portal polish + impact posts.  
**Day 8–9:** QA on Fuji, fix edges, docs.  
**Day 10:** Demo day script, seed data, screenshots.

---

## 13) Acceptance Criteria (MVP Done‑Done)
- NGO can apply; admin can approve; campaign visible.
- Donor can donate via MetaMask deep link (AVAX or USDT) on Fuji.
- Verifier records donation and triggers a Telegram receipt with explorer link.
- Impact post published by NGO is visible publicly and can be broadcast to prior donors of that campaign.

---

## 14) Future Enhancements
- Polygon/AVAX Mainnet support; ERC‑20 stablecoins on L2.
- Recurring donations; donor profiles; gift‑aid style receipts.
- Split contracts; allow multiple NGOs per campaign.
- Media proof (IPFS) for impact; verifiable claims.
- On‑ramp (Ramp/Transak) and off‑ramp integrations.
- Compliance layer (screening, jurisdiction rules).
