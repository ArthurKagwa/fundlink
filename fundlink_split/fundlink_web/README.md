# FundLink Web Backend

Django REST API backend for the FundLink humanitarian donations platform on Avalanche Fuji testnet.

## Features

- **NGO Management**: Application, approval, and profile management
- **Campaign System**: Create, publish, and manage donation campaigns  
- **Donation Tracking**: Record and verify on-chain donations
- **Impact Posts**: NGOs can post updates about campaign impact
- **Bot Integration**: API endpoints for Telegram bot integration
- **Admin Interface**: Full Django admin for platform management

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │  Django Web App │    │ Donation        │
│                 │◄──►│                 │◄──►│ Verifier        │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │   PostgreSQL    │
                        │   Database      │
                        └─────────────────┘
```

## Quick Start

1. **Setup Environment**:
   ```bash
   cd fundlink_web
   ./setup.sh
   ```

2. **Start Development Server**:
   ```bash
   source .venv/bin/activate
   python manage.py runserver
   ```

3. **Access Services**:
   - Admin Interface: http://localhost:8000/admin/
   - API Documentation: http://localhost:8000/api/
   - Health Check: http://localhost:8000/api/bot/health/

## API Endpoints

### Public Endpoints
- `GET /api/campaigns/` - List live campaigns
- `GET /api/campaigns/{id}/` - Campaign details
- `GET /api/donations/?telegram_id={id}` - Donor history
- `POST /api/ngos/apply/` - NGO application

### Bot Integration
- `POST /api/bot/notify/` - Internal notification endpoint (HMAC secured)
- `POST /api/bot/webhook/telegram/` - Telegram webhook
- `GET /api/bot/health/` - Health check

### NGO Portal (JWT Authentication Required)
- `GET /api/campaigns/` - Own campaigns
- `POST /api/campaigns/` - Create campaign
- `POST /api/impact-posts/` - Create impact post

## Configuration

Environment variables (create `.env` file):

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database (PostgreSQL for production)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=fundlink_db
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432

# Avalanche Fuji
AVALANCHE_RPC_URL=https://api.avax-test.network/ext/bc/C/rpc
AVALANCHE_CHAIN_ID=43113
USDT_CONTRACT_ADDRESS=0x5425890298aed601595a70AB815c96711a31Bc65

# Security
BOT_NOTIFY_SECRET=your-hmac-secret-for-bot-integration
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

## Data Models

### NGO
- Basic info: name, email, wallet_address, website
- Verification: docs_url, approved status
- Authentication: linked Django User account

### Campaign  
- Belongs to NGO, requires admin approval to publish
- Supports AVAX and USDT donations
- Configurable minimum amounts and token options

### Donation
- Links to NGO and optionally Campaign
- Records: token, amount, tx_hash, donor_telegram_id
- Indexed for efficient queries

### Impact Posts
- Campaign updates from NGOs
- Requires admin approval before publication

## Admin Interface

Access at `/admin/` with superuser credentials.

### Key Admin Actions:
- **Approve NGOs**: Review applications and approve legitimate organizations
- **Publish Campaigns**: Review and publish campaign proposals
- **Moderate Impact Posts**: Approve impact updates before publication
- **Monitor Donations**: View all donation activity and statistics

## Development

### Running Tests
```bash
python manage.py test
```

### Database Operations
```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Adding Sample Data
```bash
python manage.py shell
# Then run Python commands to create test NGOs, campaigns, etc.
```

## Production Deployment

1. **Set Environment Variables**:
   - Use PostgreSQL for production database
   - Set DEBUG=False
   - Configure proper SECRET_KEY
   - Set up Redis for Celery

2. **Database Setup**:
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```

3. **Process Management**:
   - Web server: Gunicorn/uWSGI
   - Background tasks: Celery workers
   - Process manager: Supervisor/systemd

## Integration with Other Components

### Telegram Bot
- Consumes `/api/campaigns/` for campaign listings
- Uses `/api/donations/?telegram_id=` for donor history
- Receives notifications via `/api/bot/notify/`

### Donation Verifier
- Creates donation records via internal API
- Triggers Telegram notifications through `/api/bot/notify/`
- Monitors Avalanche Fuji blockchain for transactions

## Security Features

- JWT authentication for NGO portal
- HMAC signature verification for internal API calls
- Input validation and SQL injection protection
- Rate limiting on public endpoints
- CORS configuration for frontend integration

## Monitoring

- Structured logging to stdout
- Health check endpoint at `/api/bot/health/`
- Django admin interface for operational monitoring
- Database query optimization with indexes