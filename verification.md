# Transaction Verification Guide

## Overview
FundLink uses an external worker to watch Avalanche Fuji and confirm donations that were initiated through the Telegram bot. Each confirmed on-chain transfer is matched back to the campaign and Telegram donor so receipts and histories stay accurate.

## Data Flow Summary
1. **Intent Registration**
   - When the bot generates a MetaMask link (`DONATE` intent), it calls the backend endpoint `/api/donations/intents/` with the campaign, NGO wallet, token, expected amount (both human-readable and base units), and the donor’s Telegram info. See `fundlink_web/donations/views.py` for the endpoint logic.
   - The backend stores this as a `DonationIntent` (model defined in `fundlink_web/donations/models.py`), which carries a UUID reference, status, and optional expiry.

2. **Chainside Verification**
   - The `donation_verifier` service (`donation_verifier/service.py`) is a Python worker using Web3. It loads configuration from environment variables via `donation_verifier/config.py`.
   - On every loop, the worker pulls pending intents through the backend API (`/api/donations/intents/list/`) and builds a lookup of `(wallet, token, value_base_units)`.
   - It scans Avalanche Fuji blocks (native AVAX transfers) and USDT `Transfer` logs, looking for matches against the lookup. Block tracking is persisted in `donation_verifier_state.json` so restarts pick up where they left off.

3. **Confirmation & Storage**
   - Once the worker matches a transaction to an intent, it POSTs to `/api/donations/confirm/` with the tx hash, value, chain metadata, sender/recipient addresses, and the intent reference.
   - The backend validates the request (internal key), links the donation to the intent and campaign, stores explorer metadata, and sets `confirmed_at`.

4. **Bot Receipts & History**
   - With the donation confirmed, the bot support flow (`CONFIRM_DONATION` intent) fetches the most recent donation and thanks the user. The donor history endpoint and serializer now include explorer URLs and campaign info so everything remains traceable.

## Configuration
Set these keys (typically in `.env`):

| Variable | Description |
|----------|-------------|
| `FUJI_RPC_URL` | Avalanche Fuji RPC endpoint the worker should poll |
| `BACKEND_URL` | Base URL of the Django backend (e.g., `https://backend.fundlink.example`) |
| `INTERNAL_API_KEY` | Shared secret used by the worker and bot for internal endpoints |
| `USDT_CONTRACT_ADDRESS` | Fuji USDT contract (optional, enables ERC-20 monitoring) |
| `VERIFIER_POLL_INTERVAL` | Seconds between polling cycles (default 15) |
| `VERIFIER_BLOCK_BATCH` | Number of blocks to scan per iteration |
| `VERIFIER_START_BLOCK` | Optional manual start height |
| `VERIFIER_STATE_PATH` | Path to JSON file storing last processed block |

## Deploying the Worker
1. Install dependencies: `pip install -r requirements-all.txt` (this pulls the worker requirements too).
2. Ensure the runtime directory is writable so the state file can be created.
3. Run a dry check: `python -m donation_verifier.main --run-once` (confirms configuration and matching logic).
4. For production, run continuously via your process manager, e.g. systemd:
   ```ini
   [Service]
   WorkingDirectory=/opt/fundlink
   EnvironmentFile=/opt/fundlink/.env
   ExecStart=/opt/fundlink/.venv/bin/python -m donation_verifier.main
   Restart=always
   ```

## Monitoring & Troubleshooting
- Logs are emitted to stdout with timestamps. Look for lines like `Confirmed donation via intent ...`.
- If the worker reports “Matching donation intent not found,” confirm the bot is registering intents (check `/api/donations/intents/list/`).
- Duplicate confirmation attempts return the existing donation data with HTTP 200 — safe for idempotent retries.
- Ensure `INTERNAL_API_KEY` matches across bot, verifier, and backend; a mismatch yields 401 responses.
- Use `fundlink_web/donations/tests/test_donation_intents.py` as reference for minimal API interactions when debugging.

## File References
- `fundlink_web/donations/models.py` — defines `Donation` and `DonationIntent` models.
- `fundlink_web/donations/views.py` — internal APIs for intents and confirmations.
- `donation_verifier/service.py` — main worker loop and block scanning.
- `telbot_llm/telbot_llm/response_agent.py` — registers intents and handles donor receipts.
- `fundlink_web/donations/tests/test_donation_intents.py` — unit tests covering intent + confirmation flows.

Keeping the worker running alongside the backend ensures every on-chain donation is linked back to campaigns and donors automatically.
