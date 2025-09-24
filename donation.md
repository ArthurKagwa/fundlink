# First‑Time Donor Flow (Payment Only)

**Scope:** Telegram donor → campaign selection → amount selection → MetaMask deep link returned. *No verifier/receipt in this doc.*

---
## 0) Outcomes & Constraints
- **Outcome:** Donor gets a valid **Donate with MetaMask** deep link in ≤ 3 taps (or one free‑text message + one tap).
- **Chain/Token:** Avalanche Fuji (C‑Chain), default token **AVAX (18 decimals)**; optionally **USDT (6 decimals)**.
- **Minimal Friction:** Prefer buttons; accept free‑text (e.g., “donate 0.0001 to life”).
- **Safety:** Validate wallet addresses, respect campaign min amount, sanitize amounts.

---
## 1) Canonical Conversation (Happy Path)
1. **/start** → Welcome + buttons: *View campaigns*, *My history*.
2. **View campaigns** → Bot lists active, approved campaigns (title • NGO • min • target) with **Select** buttons.
3. **Select campaign** → Bot shows compact details + **suggested amounts** (e.g., 0.0001, 0.001, Custom) and **token toggle** (AVAX ↔ USDT).
4. **Choose amount** → Bot immediately returns **Inline button**: *Donate with MetaMask* (deep link). Done.

> Free‑text fast path: “donate 0.0001 to life” → Resolve campaign “Life” → generate deep link → reply with button.

---
## 2) Core Intents → Required Data → Tools

### A. List Campaigns
- **Intent:** "view campaigns"
- **Needs:** Active campaigns (id, title, ngo, wallet, min_amount, tokens)
- **Tool:** `list_campaigns()` (backend)
- **Memory to set:** `last_campaign_listed_ids`, `last_campaign_listing_ts`

### B. Select Campaign
- **Intent:** pick by button OR parse title/id from text
- **Needs:** Campaign detail
- **Tool:** `get_campaign(campaign_id)` (backend)
- **Memory to set:** `current_campaign_id`, `current_campaign_wallet`, `current_campaign_token_options`, `current_campaign_min`

### C. Amount Selection
- **Intent:** choose a suggested amount or provide custom numeric amount
- **Needs:** Min amount, token decimals
- **No backend call** (local validation)
- **Memory to set:** `pending_amount`, `pending_token` (default AVAX), `pending_decimals` (18 or 6)

### D. Deep Link Generation
- **Intent:** create MetaMask link
- **Tool:** `make_metamask_deep_link(address, amount, token?, decimals?)` (local)
- **Inputs:** `current_campaign_wallet`, `pending_amount`, `pending_token`, `pending_decimals`
- **Output:** URL string

---
## 3) Tooling Specs & Behaviours

### 3.1 Backend Tools (HTTP via router)
- `list_campaigns()` → `[ {id, title, ngo_name, wallet_address, min_amount, token_options} ]`
- `get_campaign(campaign_id)` → `{id, title, ngo_name, wallet_address, min_amount, token_options}`
- `user_exists(telegram_id)` / `register_user(telegram_id, username)` (silent on /start or first message)

### 3.2 Local Tools
- `make_metamask_deep_link(address:str, amount:float, token:str|None, decimals:int=18) -> str`
  - If `token` provided, append `&contractAddress=<token>`; else native AVAX.
  - Convert human amount → wei using `Decimal` to avoid FP drift.

### 3.3 Validation Helpers
- `is_valid_checksum_address(address)` (optional for bot; guaranteed on backend)
- `sanitize_amount(text) -> Decimal|None` (extract first decimal number; reject negatives, NaN, overly precise > decimals)
- Clamp to `min_amount` if provided; otherwise error with suggested buttons.

---
## 4) Memory Model (Per‑User)
- **Ephemeral (session cache, TTL ~30 min):**
  - `current_campaign_id`
  - `current_campaign_wallet`
  - `current_campaign_min`
  - `current_campaign_token_options`
  - `pending_amount`
  - `pending_token` (default "AVAX")
  - `pending_decimals` (18 default)
- **Sticky (days):**
  - `last_campaign_listed_ids`
  - `last_campaign_listing_ts`
  - `last_used_token` (remember USDT preference)

> Evict ephemeral memory on `/cancel`, `/start` (optional), or after deep link is generated.

---
## 5) Disambiguation Rules
- **No current campaign:**
  - If only one active campaign → assume it, confirm inline: “Donating to *Life* by *eco*?” [Yes] [Pick another]
  - Else → present top 5 campaigns as buttons.
- **Ambiguous title in text:** Show top matches with NGO name + ID.
- **Amount < min:** Reply: “Minimum is 0.00002 AVAX for *Life*. Pick one:” → buttons with `[min] [min×5] [Custom]`.
- **Token unspecified:** Use `last_used_token` or default AVAX; include a toggle button.

---
## 6) Message UX (Copy Patterns)
- **Campaign list:**
  - "Here are live campaigns (pick one):\n1) Life — eco (min 0.00002 AVAX)"
- **Campaign detail:**
  - "*Life* — eco\nMin: 0.00002 AVAX • Target: 0.004\nChoose an amount:" + buttons `[0.0001] [0.001] [Custom]` + token toggle `[AVAX • USDT]`
- **Amount confirmation:**
  - "Great. 0.0001 AVAX to *Life*. Tap to donate:" + **[Donate with MetaMask]**
- **Min error:**
  - "That’s below the minimum (0.00002 AVAX). Try one of these:" + suggested buttons.
- **Fallback (tool error):**
  - "Couldn’t generate a link right now. Here’s the raw address + amount you can paste in MetaMask: <address> • 0.0001 AVAX (Fuji)."

---
## 7) LLM System/Tool Instructions (Concise)
- **System guidance:**
  - Keep replies short. Prefer buttons. If user expresses intent to donate, ensure `current_campaign_id` and `pending_amount` are set before generating a deep link.
  - If campaign unknown, call `list_campaigns` and ask user to pick (buttons); if only one, assume it and confirm.
  - When amount is provided in text, extract numeric amount; compare with campaign `min_amount`; if below, propose `min_amount` and a larger option.
  - Default token = AVAX (18). If user says USDT, set token to Fuji USDT (6 decimals).
  - Call `make_metamask_deep_link` with `(address, amount, token?, decimals)` and respond with a **single button** labelled **Donate with MetaMask**; do not add extra steps.

- **Few‑shot style examples (internal):**
  - User: "donate 0.0001 to life" → Tools: `get_campaign(id=1)` → `make_metamask_deep_link(address=..., amount=0.0001)` → Reply button.
  - User: "give 10 usdt to clean water" → Resolve USDT (decimals=6, token=<USDT_CONTRACT>) → deep link.

---
## 8) Button Layouts
- **Campaign list:** rows of `[Title (NGO)]` → data embeds `campaign_id`
- **Campaign detail:** `[0.0001] [0.001] [Custom]` • `[AVAX • USDT]`
- **Donate:** `[Donate with MetaMask] (url=<deep_link>)`

---
## 9) Pseudocode (Handler Level)
```
text = update.message.text
ensure_user_registered(tg_id)
intent = nlp_or_rules(text)

if intent == VIEW_CAMPAIGNS:
    camps = list_campaigns()
    show_campaign_buttons(camps)
    return

if intent == SELECT_CAMPAIGN:
    camp = get_campaign(campaign_id)
    set_memory(camp)
    show_amount_buttons(camp)
    return

if intent == DONATE_FREE_TEXT:
    amount = extract_amount(text)
    camp = resolve_campaign_from_context_or_title(text)
    if not camp: disambiguate(); return
    if amount < camp.min: suggest_min_buttons(); return
    link = make_metamask_deep_link(camp.wallet, amount, token, decimals)
    reply_with_button(link)
    clear_ephemeral()
    return

if intent == PICK_AMOUNT_BUTTON:
    amount = button_value
    camp = memory.current_campaign
    link = make_metamask_deep_link(camp.wallet, amount, token, decimals)
    reply_with_button(link)
    clear_ephemeral()
```

---
## 10) Edge Cases & Guards
- Empty campaign list → graceful message: “No live campaigns yet.”
- Wallet missing on campaign → log error; show fallback text with admin contact.
- Float parsing issues → ask user to re‑enter amount or tap suggested buttons.
- Large precision (> decimals) → round down to allowed decimals and show the displayed value.

---
## 11) Test Matrix (Payment Only)
- 1 live campaign, user types: "donate 0.0001" → assumes that campaign (confirm) → deep link.
- Multiple campaigns, ambiguous text: show disambiguation.
- Below min amount: rejection + suggestions.
- USDT path: decimals = 6, token address present.
- Button‑only path: select → amount button → link.

---
## 12) Telemetry (Minimal)
- Counters: `campaign_list_shown`, `campaign_selected`, `amount_chosen`, `deep_link_generated`.
- Histogram: `deep_link_latency` (ms from amount selection → reply).

---
## 13) Security Notes
- Never echo private keys.
- Validate checksum addresses server‑side; bot trusts backend for wallet hygiene.
- Anti‑abuse: rate limit deep‑link generation per user (e.g., 10/min) to prevent spam.

---
## 14) Done‑Done (Payment Layer)
- Selecting a campaign and amount returns a valid MetaMask deep link button within one interaction step, across both **button** and **free‑text** flows.

