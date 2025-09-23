# FundLink Baseline Documentation

## Current State Overview
FundLink is a humanitarian donations MVP built for Avalanche Fuji testnet with a focus on minimalistic UI/UX design. The system consists of three main components: Django web backend, Telegram bot, and blockchain donation verifier.

## Architecture

### Core Components
1. **Django Web Application** (`fundlink_web/`)
   - REST API backend using Django REST Framework
   - Minimalistic web interface with essential-only features
   - Admin panel for NGO and campaign management
   - Postgres database integration

2. **Telegram Bot** (`tel_bot/`)
   - Python-telegram-bot implementation
   - Campaign browsing and MetaMask deep link generation
   - User registration and donation tracking

3. **Donation Verifier** (`donation_verifier/`)
   - Web3.py-based blockchain monitoring
   - Avalanche Fuji testnet transaction verification
   - Automated donation confirmation and notifications

## UI/UX Design Philosophy

### Minimalistic Approach
The web frontend follows a "less is more" philosophy with:

- **Clean Typography**: System fonts only, no custom font loading
- **Minimal Color Palette**: Black/white/gray with minimal color accents
- **Essential Features Only**: Removed unnecessary animations, graphics, and decorative elements
- **Mobile-First**: Responsive design that works on all devices
- **Fast Loading**: No heavy frameworks, minimal CSS, optimized for performance

### Key Interface Elements

**Base Template** (`templates/base.html`):
- Simple header with logo and navigation
- Inline CSS for zero external dependencies
- Clean typography and spacing
- Accessible focus states

**Home Page** (`templates/home.html`):
- Direct value proposition
- Two primary actions: View Campaigns, Register NGO
- Three key benefits in card format
- Dynamic campaign loading via API

**Campaign List** (`templates/campaigns/list.html`):
- Search functionality
- Clean card-based layout
- Essential information only: title, NGO, description, target amount

**Campaign Detail** (`templates/campaigns/detail.html`):
- Campaign details and donation stats
- Simplified donation form with MetaMask integration
- Recent donations display
- Direct blockchain transaction links

**NGO Registration** (`templates/ngos/apply.html`):
- Essential fields only
- Clear requirements
- Single-page form submission

## Technology Stack

### Backend
- **Django 5.2.6**: Web framework
- **Django REST Framework**: API endpoints
- **PostgreSQL**: Primary database
- **python-telegram-bot**: Telegram integration
- **web3.py**: Blockchain interaction

### Frontend
- **Vanilla JavaScript**: No frameworks
- **Inline CSS**: Minimal styling approach
- **System Fonts**: No external font dependencies
- **Responsive Grid**: CSS Grid and Flexbox

### Blockchain
- **Avalanche Fuji Testnet**: C-Chain
- **MetaMask Integration**: Deep links for donations
- **AVAX & USDT Support**: Native and ERC-20 tokens

## API Endpoints

### Public Endpoints
- `GET /api/campaigns/` - List active campaigns
- `GET /api/campaigns/{id}/` - Campaign details
- `GET /api/donations/` - Donation history (filterable)

### Admin Endpoints
- `POST /api/admin/ngos/{id}/approve/` - Approve NGO
- `POST /api/admin/campaigns/{id}/publish/` - Publish campaign

### Bot Integration
- `POST /api/bot/register-user/` - Register Telegram user
- `POST /api/bot/notify/` - Send donation notifications

## Database Schema

### Core Models
- **NGO**: Organization details, wallet address, verification status
- **Campaign**: Fundraising campaigns with target amounts
- **Donation**: Transaction records with blockchain verification
- **BotUser**: Telegram user management

## Security Considerations

### Authentication
- Django Admin for staff access
- Token-based authentication for API endpoints
- HMAC verification for internal bot communications

### Validation
- Wallet address checksumming
- Input sanitization and validation
- Rate limiting on public endpoints

### Blockchain Security
- Transaction verification before confirmation
- Wallet address validation
- Testnet environment for safety

## Performance Optimizations

### Frontend
- Minimal CSS (< 2KB)
- No external dependencies
- Lazy loading for campaign data
- Mobile-optimized responsive design

### Backend
- Database query optimization
- API pagination
- Efficient serializers
- Minimal response payloads

## Deployment Considerations

### Environment Variables
- `TELEGRAM_BOT_TOKEN`: Bot authentication
- `BACKEND_URL`: API base URL
- `DATABASE_URL`: PostgreSQL connection
- `AVALANCHE_RPC_URL`: Blockchain endpoint

### Infrastructure
- Django application server
- PostgreSQL database
- Background worker for verification
- Webhook endpoint for Telegram

## Current Limitations

1. **Testnet Only**: Fuji testnet implementation
2. **Manual NGO Approval**: Requires admin intervention
3. **Basic Error Handling**: Minimal error recovery
4. **Limited Token Support**: AVAX and USDT only

## Future Enhancements

1. **Mainnet Deployment**: Production-ready implementation
2. **Automated KYC**: NGO verification automation
3. **Additional Tokens**: Support for more cryptocurrencies
4. **Impact Tracking**: Campaign progress and reporting
5. **Multi-language Support**: Internationalization

## Development Status

- ✅ Core architecture implemented
- ✅ Minimalistic UI/UX completed
- ✅ Basic API endpoints functional
- ✅ Telegram bot integration
- ⏳ Blockchain verifier implementation
- ⏳ Admin workflow testing
- ⏳ End-to-end integration testing

Last Updated: September 23, 2025

## LLM Assistant Integration (telbot_llm)

### Purpose
Adds an opt-in intelligent assistant layer that can: 
- Interpret natural-language donor / NGO queries in Telegram.
- Safely fetch authoritative data via constrained tool/function calls instead of hallucinating.
- Provide concise, policy-aligned answers (no fabricated wallet addresses, tx hashes, or campaign stats).

### Components
- `telbot_llm/llm_client.py`: Orchestrates model calls with primary + fallback Together models.
- `telbot_llm/tools.py`: OpenAI/Together-compatible function schemas (campaigns, donations, user registration, NGO application, donor notification).
- `telbot_llm/router.py`: HTTP bridge with timeout + error handling to Django backend.
- `telbot_llm/handlers.py`: Telegram message handler integrating LLM + tool execution + graceful degradation.
- `telbot_llm/errors.py`: Structured exception taxonomy (`LLMError`, `BackendAPIError`, `ToolExecutionError`).
- `telbot_llm/telemetry/metrics.py`: Optional Prometheus counters & latency histogram.

### Supported Tool Functions
| Name | Description | Required Args |
|------|-------------|---------------|
| `list_campaigns` | List active campaigns | – |
| `get_campaign` | Fetch campaign detail | `campaign_id` |
| `get_donations` | Donation history for a Telegram user | `telegram_id` |
| `register_user` | Idempotent Telegram user registration | `telegram_id` |
| `notify_donor` | Send donor message (secured) | `telegram_id`, `message` |
| `apply_ngo` | Submit NGO application | `name`, `email`, `wallet_address` |

### Safety / Guardrails
- System prompt enforces: no fabrication of blockchain artifacts, concise answers, tool usage for facts.
- Only whitelisted tool schema exposed; arbitrary HTTP or code execution is not available to the model.
- Backend re-validates inputs (e.g., wallet address format, campaign existence).
- Fallback model ensures continuity if primary model request fails.

### Error Handling Strategy
| Layer | Failure | User Impact | Mitigation |
|-------|---------|-------------|------------|
| LLM API | Network / rate limit | Generic service issue message | Retry with fallback model |
| Backend API | 4xx/5xx | Service issue message | Inline snippet truncated; no sensitive leakage |
| Tool Execution | Unexpected exception | Safe generic error | Structured exception raised |

### Telemetry (Prometheus)
- Counter: `telbot_llm_requests_total`
- Histogram: `telbot_llm_response_latency_seconds`
- Opt-out via `DISABLE_METRICS=1`.

### Environment Variables (Additions)
| Variable | Default | Purpose |
|----------|---------|---------|
| `TOGETHER_API_KEY` | – | Auth for Together models |
| `TOGETHER_MODEL` | llama 70B instruct turbo | Primary model id |
| `TOGETHER_MODEL_FALLBACK` | llama 8B instruct | Fallback model id |
| `LLM_TEMPERATURE` | 0.2 | Response creativity control |
| `HTTP_TIMEOUT` | 20 | Seconds for backend HTTP calls |
| `DISABLE_METRICS` | unset | Disable Prometheus objects |

### Integration Steps (Telegram Bot)
1. Install dependencies (`together`, `httpx`, `prometheus_client`, `python-telegram-bot`).
2. Export required env vars (`TOGETHER_API_KEY`, `BACKEND_URL`, etc.).
3. Add handler:
   ```python
   from telbot_llm.handlers import handle_message
   app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
   ```
4. Deploy with metrics endpoint (future enhancement) or rely on internal registry for scraping sidecar.

### Current Limitations (LLM Layer)
1. No streaming token responses yet (single completion per turn).
2. No persistent multi-turn memory beyond provided recent history (memory store TBD).
3. No rate limiting at LLM layer (relies on upstream Telegram + backend throttling).
4. Tool argument schema not yet auto-validated client-side (backend still authoritative).

### Planned Enhancements
1. Redis or in-memory TTL cache for `list_campaigns` to reduce latency & cost.
2. Streaming partial responses to Telegram (edit message pattern).
3. Conversation memory window persisted (Redis) keyed by Telegram user id.
4. Guardrail validation (JSON Schema) before invoking backend.
5. Additional tools: `search_campaigns`, `latest_impact_posts`, `estimate_gas` (if needed for UX clarity).

### Rationale
The assistant reduces friction for donors (discover campaigns, recall past donations) and NGOs (application guidance) without expanding the public API surface or compromising verifiability. Tool calling enforces a deterministic boundary: model language generation only; facts come from backend or are omitted.

