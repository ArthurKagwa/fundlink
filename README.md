# FundLink - Humanitarian Donations on Avalanche

> Minimalistic, transparent cryptocurrency donations for verified NGOs on Avalanche Fuji testnet.

## Overview

FundLink enables transparent humanitarian donations using cryptocurrency on the Avalanche blockchain. The platform features a clean, minimalistic interface focused on essential functionality only.

### Unified Environment & Dependencies

All components now share a single root `.env` (see `.env.example`). A unified bearer `INTERNAL_API_KEY` secures internal service calls (Telegram bot, LLM assistant, future donation verifier). Legacy `BACKEND_API_KEY` and `BOT_NOTIFY_SECRET` will be phased out; `BOT_NOTIFY_SECRET` is still accepted for HMAC calls to `/api/bot/notify/` as fallback.

Install all dependencies across the stack:
```bash
pip install -r requirements-all.txt
```

Primary new variables:
- `INTERNAL_API_KEY`: Required for internal Authorization: `Bearer <key>` headers
- `TOGETHER_MODEL_FALLBACK`: Optional backup LLM model

Migration steps (manual):
1. Create `.env` at repo root from `.env.example` and consolidate former per-directory env files.
2. Replace any deployment secrets referencing `BACKEND_API_KEY` with `INTERNAL_API_KEY`.
3. (Optional) Keep `BOT_NOTIFY_SECRET` during transition if external HMAC caller still active.

## Key Features

- **🌐 Minimalistic Web Interface**: Clean, fast-loading design with zero unnecessary elements
- **🤖 Telegram Bot Integration**: Easy donation discovery and MetaMask deep links
- **🔗 Blockchain Transparency**: All donations verified and tracked on-chain
- **✅ Verified NGOs**: Manual verification process ensures legitimacy
- **💰 Multi-Token Support**: AVAX and USDT donations supported
- **📱 Mobile-First Design**: Optimized for all devices with responsive layout

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │  Telegram Bot   │    │ Donation Verify │
│                 │    │                 │    │                 │
│ • Campaign List │    │ • Browse Camps  │    │ • Monitor Chain │
│ • NGO Register  │    │ • MetaMask Link │    │ • Confirm Txns  │
│ • Minimal UI    │    │ • Notifications │    │ • Send Alerts   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Django Backend  │
                    │                 │
                    │ • REST API      │
                    │ • Admin Panel   │
                    │ • Database      │
                    │ • User Auth     │
                    └─────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL
- MetaMask wallet (for donations)
- Telegram account (for bot interaction)

### Installation

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd fundlink
   ```

2. **Setup Django Backend**
   ```bash
   cd fundlink_web
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver
   ```

3. **Setup Telegram Bot**
   ```bash
   cd tel_bot
   pip install -r requirements.txt
   # Configure TELEGRAM_BOT_TOKEN in .env
   python bot.py
   ```

4. **Setup Donation Verifier**
   ```bash
   cd donation_verifier
   pip install -r requirements.txt
   # Configure Avalanche RPC settings
   python verifier.py
   ```

### Environment Configuration

Use the single root `.env` (see `.env.example`) and define at least:
```
SECRET_KEY=change-me
DEBUG=true
INTERNAL_API_KEY=your-shared-internal-key
BACKEND_URL=http://localhost:8000
TELEGRAM_BOT_TOKEN=your-telegram-token
AVALANCHE_RPC_URL=https://api.avax-test.network/ext/bc/C/rpc
```
Add LLM settings (`TOGETHER_API_KEY`, etc.) if using the assistant component.

## Usage

### For Donors

1. **Web Interface**: Visit the website to browse campaigns
2. **Telegram Bot**: Use `/campaigns` to see available causes
3. **Donate**: Click MetaMask links to send AVAX or USDT
4. **Track**: View transaction confirmations and impact

### For NGOs

1. **Register**: Apply via web form with organization details
2. **Verification**: Wait for manual admin approval
3. **Create Campaigns**: Add fundraising campaigns via admin
4. **Receive Donations**: Monitor incoming transactions
5. **Report Impact**: Update supporters on campaign progress

### For Administrators

1. **Review Applications**: Verify NGO legitimacy and documentation
2. **Approve Organizations**: Enable NGOs to receive donations
3. **Monitor System**: Track donations and system health
4. **Moderate Content**: Ensure campaign quality and compliance

## API Documentation

### Public Endpoints

**List Campaigns**
```http
GET /api/campaigns/
```

**Campaign Details**
```http
GET /api/campaigns/{id}/
```

**Donation History**
```http
GET /api/donations/?campaign={id}&telegram_id={id}
```

### Authentication Required

**NGO Management**
```http
POST /api/admin/ngos/{id}/approve/
POST /api/admin/campaigns/{id}/publish/
```

**Bot Integration**
```http
POST /api/bot/register-user/
POST /api/bot/notify/
```

## UI/UX Design Principles

### Minimalistic Philosophy

The interface follows strict minimalism principles:

- **No Frameworks**: Pure HTML/CSS/JS for maximum performance
- **System Fonts**: No external font loading
- **Essential Colors**: Black/white/gray palette only
- **Clean Typography**: Clear hierarchy and readable text
- **Fast Loading**: < 2KB CSS, no heavy assets
- **Mobile-First**: Responsive design that works everywhere

### Key Design Decisions

1. **Single-Page Forms**: Minimize clicks and confusion
2. **Direct Actions**: Clear call-to-action buttons
3. **Essential Information**: Show only what users need
4. **Progressive Enhancement**: Works without JavaScript
5. **Accessibility**: Proper focus states and semantic HTML

## Security

### Blockchain Security
- Testnet environment for safety
- Wallet address validation and checksumming
- Transaction verification before confirmation
- Public blockchain transparency

### Application Security
- Django security best practices
- Input validation and sanitization
- CSRF protection
- Secure authentication tokens

### Privacy
- Minimal data collection
- No tracking scripts
- Optional user information
- Transparent data usage

## Contributing

### Development Workflow

1. **Fork Repository**: Create your own copy
2. **Feature Branch**: Work on dedicated branches
3. **Test Locally**: Verify all components work
4. **Documentation**: Update relevant docs
5. **Pull Request**: Submit for review

### Code Standards

- **Python**: Follow PEP 8 styling
- **JavaScript**: Use vanilla JS, no frameworks
- **CSS**: Keep minimal, use system fonts
- **HTML**: Semantic markup, accessibility-first

## Deployment

### Production Considerations

1. **Database**: PostgreSQL with connection pooling
2. **Static Files**: CDN or efficient serving
3. **Environment**: Secure secret management
4. **Monitoring**: Error tracking and health checks
5. **Backup**: Regular database and data backups

### Recommended Stack

- **Application**: Railway, Render, or Fly.io
- **Database**: Managed PostgreSQL
- **Monitoring**: Sentry for error tracking
- **CDN**: CloudFlare for static assets

## Support

### Getting Help

- **Documentation**: Check this README and BASELINE.md
- **Issues**: Open GitHub issues for bugs
- **Discussions**: Use GitHub discussions for questions
- **Contact**: Reach out via project maintainers

### Troubleshooting

**Common Issues:**

1. **Database Connection**: Check PostgreSQL settings
2. **Bot Not Responding**: Verify Telegram token
3. **Donations Not Confirming**: Check RPC connection
4. **Styles Not Loading**: Verify static file serving

## License

This project is open source. See LICENSE file for details.

## Roadmap

### Phase 1 ✅
- Core architecture
- Minimalistic UI implementation
- Basic API endpoints
- Telegram bot integration

### Phase 2 ⏳
- Blockchain verifier completion
- End-to-end testing
- Admin workflow refinement
- Performance optimization

### Phase 3 🔄
- Mainnet deployment preparation
- Advanced security auditing
- Multi-language support
- Enhanced impact tracking

---

**Built with ❤️ for humanitarian impact**

*Last updated: September 23, 2025*
