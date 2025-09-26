# Dual-Agent Bot Architecture (Intent Agent + Response Agent)

## Purpose
Deliver a **reliable, low-latency** Telegram donation experience by separating **understanding** from **doing**:
- **Intent Agent**: classifies the user’s goal and extracts slots (amount, token, campaign).
- **Response Agent**: executes business logic and renders UI (buttons, deep links), calling your backend/tools.

This split trims hallucinations, stabilises tool usage, and makes the system easy to test and evolve.

---

## High-Level Flow

```
User ──► Intent Agent (JSON only)
           │
           ▼
   Intent JSON {intent, entities, confidence}
           │
           ▼
  Response Agent (deterministic)
  ├─ calls backend tools (list_campaigns, get_campaign, get_donations)
  ├─ calls local tools (make_metamask_deep_link)
  └─ renders Telegram UI (buttons, messages)
           │
           ▼
         User
```

**Scope (payment-first):** up to donation deep link; receipts handled later by verifier.

---

## Intents & Entities

### Supported Intents
- `VIEW_CAMPAIGNS` – list live campaigns.
- `SELECT_CAMPAIGN` – user picked a specific campaign (by id/title).
- `DONATE` – user wants to donate a specified/unspecified amount/token to a campaign.
- `HISTORY` – show donor history.
- `HELP` / `UNKNOWN` – fallback.

### Entity Slots
- `campaign_id` (int)  
- `campaign_title` (string)
- `amount` (number; human units)
- `token` (enum: `AVAX` | `USDT`)
- `confidence` (0.0–1.0)

---

## Data Contracts

### Intent Agent Output (strict JSON)
```json
{
  "intent": "DONATE",
  "entities": {
    "campaign_title": "life",
    "amount": 0.0001,
    "token": "AVAX"
  },
  "confidence": 0.92
}
```

### Response Agent Inputs
- `intent_json` (above)
- `user_state` (ephemeral per Telegram ID):
  ```json
  {
    "current_campaign_id": 1,
    "current_campaign": { /* cached detail */ },
    "pending_token": "AVAX",
    "pending_decimals": 18,
    "last_used_token": "AVAX"
  }
  ```

### Response Agent Outputs
- Telegram message + InlineKeyboard buttons  
- Optional deep link payload:
  ```json
  { "deep_link": "https://metamask.app.link/send/0x...?...",
    "token": "AVAX", "amount": 0.0001 }
  ```

---

## Tools & Responsibilities

### Backend Tools (HTTP via your router)
- `list_campaigns()` → list (supports pagination).
- `get_campaign(campaign_id)` → detail.
- `get_donations(telegram_id)` → history.

### Local Tools
- `make_metamask_deep_link(address, amount, token?, decimals=18)`  
  Returns `{ deep_link, error }`.

### UI Helpers
- `render_campaign_buttons(campaigns)`  
- `render_amount_buttons(campaign, token)`  
- `render_donate_button(deep_link)`  

*(UI helpers aren’t LLM tools — they’re pure Python in the Response Agent.)*

---

## Prompts

### Intent Agent (System Prompt)
- “Extract **only** intent and entities as strict JSON (`{intent, entities, confidence}`). No prose.”
- “If amount or token unspecified, omit the field. Default AVAX is applied by the Response Agent.”
- “Confidence < 0.6 → use `UNKNOWN` unless the user directly clicked a button.”
- Few-shots:
  - “campaigns” → `{"intent":"VIEW_CAMPAIGNS","entities":{},"confidence":0.98}`
  - “donate 0.0001 to life” → DONATE + amount + title + token AVAX
  - “give 10 usdt to life” → DONATE + amount 10 + token USDT + title

### Response Agent (No LLM needed)
- Deterministic Python that consumes the JSON and executes tools/UI.

---

## Control Logic (Response Agent)

1) **VIEW_CAMPAIGNS**  
   - `list_campaigns()`  
   - If none → “No live campaigns yet.”  
   - Else render buttons: `Title — NGO (min …)` with callback `a:sel|cid:{id}`.

2) **SELECT_CAMPAIGN**  
   - Resolve by `campaign_id` or fuzzy match `campaign_title`.  
   - Cache `current_campaign` in state.  
   - Render amount choices: `[min] [min×5] [min×10]` + token toggle (AVAX↔USDT).

3) **DONATE**  
   - Ensure campaign context (from state or by title match).  
   - Validate/min-clamp amount; default token to AVAX if absent.  
   - `make_metamask_deep_link(wallet, amount, token_contract, decimals)`  
   - Show **single** button: “🦊 Donate with MetaMask”, plus “➕ Add Fuji” helper.

4) **HISTORY**  
   - `get_donations(telegram_id)` → compact list (last 5) with dates and titles.

5) **UNKNOWN/HELP**  
   - Show small menu: “📜 Campaigns”, “📋 My History”.

---

## Callback Handling
Buttons carry compact `callback_data`:
- `{"a":"sel","c":1}` → select campaign id 1  
- `{"a":"amt","c":1,"v":"0.0001"}` → donate amount  
- `{"a":"tok","c":1,"t":"USDT"}` → token toggle

Handler decodes, updates `user_state`, and executes the appropriate branch. No Intent Agent needed for callbacks.

---

## Precision, Validation, and Defaults
- **Amounts:** Use `Decimal` for scaling; AVAX 18 decimals, USDT 6.  
- **Min amounts:** Reject under-min with helpful buttons.  
- **Tokens:** Default AVAX; remember `last_used_token` per user.  
- **Wallets:** Trust backend to store checksummed addresses.

---

## Error-Handling & Guardrails
- **Intent JSON invalid:** retry once; else fallback to menu.  
- **Ambiguous title:** show top matches (Title — NGO) with buttons.  
- **Empty campaign list:** friendly no-data message.  
- **Link build failure:** show raw address + amount and the Fuji chain reminder.

---

## Observability
- Metrics (labels by intent):  
  - `intent_extracted_total`, `deep_link_generated_total`, `campaign_list_shown_total`.  
  - `latency_ms` from intent parse → UI render.  
- Logs: `(tg_id, intent, entities, outcome, errors)`; redact PII.

---

## Security Notes
- No secrets in prompts or messages.  
- Internal endpoints use `X-INTERNAL-KEY` (plan HMAC v2).  
- Rate-limit deep-link generation (e.g., 10/min/user).  
- Never echo private keys; keep PII minimal.

---

## Testing Matrix

| Case | Input | Expected |
|---|---|---|
| List | “campaigns” | Campaign buttons (≤10); no raw JSON/code |
| Donate AVAX | “donate 0.0001 to life” | Deep link button + Fuji reminder |
| Donate USDT | “give 10 usdt to life” | Deep link (USDT contract) |
| Ambiguous | “donate to l” (2 matches) | Disambiguation buttons |
| Under-min | “donate 0.00001 to life” | Explain min + suggest buttons |
| Callbacks | click amount button | Deep link button in one step |

---

## Deployment Notes
- **Intent Agent**: small model, low temperature (≈0.2), strict JSON output.  
- **Response Agent**: Python module; no model call on happy path.  
- Cache `list_campaigns` 30–60s to reduce backend load during bursts.

---

## Why This Works
- **Determinism:** the doer doesn’t improvise; it just executes.  
- **Speed:** tiny intent pass + direct tool calls.  
- **Robustness:** buttons and callbacks bypass NLP entirely for the heavy lifting.  
- **Testability:** you can unit-test response paths with canned intents.

---

## Next Steps
- Add a tiny **free-text rule** for “donate X to Y” when Intent Agent is uncertain.  
- Expand to **receipt flow**: verifier posts to backend → bot sends receipt with Snowtrace link.  
- Add **analytics** (which amounts/buttons convert best) and **A/B** suggested amounts.
