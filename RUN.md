# FundLink Local Development Setup

This guide will help you set up and run the FundLink humanitarian donations platform locally using Python virtual environments.

## Prerequisites

- Python 3.11+
- Git
- PostgreSQL (optional, SQLite is default)
- Redis (optional, for Celery tasks)
- A Telegram bot token (optional for testing without bot)

## Quick Start

### 1. Clone and Setup Environment

```bash
git clone https://github.com/ArthurKagwa/fundlink.git
cd fundlink

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-all.txt

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment Variables

Edit the `.env` file with your configuration:

```bash
# Required: Change the secret key
SECRET_KEY=your-super-secret-django-key-here

# Required: Set a secure internal API key
INTERNAL_API_KEY=your-secure-internal-api-key

# Database (SQLite default - no setup required)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Optional: For PostgreSQL instead of SQLite
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=fundlink
# DB_USER=fundlink
# DB_PASSWORD=fundlink
# DB_HOST=localhost
# DB_PORT=5432

# Optional: Add your Telegram bot token (get from @BotFather)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# Optional: For development, you can use ngrok for webhook testing
TELEGRAM_WEBHOOK_URL=https://your-ngrok-url.ngrok.io/bot/api/webhook/telegram/
PUBLIC_WEBHOOK_BASE=https://your-ngrok-url.ngrok.io

# Optional: Together AI API key for LLM features
TOGETHER_API_KEY=your-together-api-key

# Optional: Redis for Celery (if not set, some features may be disabled)
REDIS_URL=redis://localhost:6379/0
```

### 3. Setup Database and Web Backend

```bash
# Navigate to web backend
cd fundlink_web

# Run database migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Start Django development server
python manage.py runserver 0.0.0.0:8000
```

Keep this terminal open - the web backend will be running on http://localhost:8000

### 4. Start Telegram Bot (Optional)

Open a new terminal:

```bash
cd /path/to/fundlink
source .venv/bin/activate

# Navigate to bot directory
cd telbot_llm

# Start the bot
python run_bot.py
```

### 5. Start Donation Verifier (Optional)

Open another new terminal:

```bash
cd /path/to/fundlink
source .venv/bin/activate

# Navigate to verifier directory
cd donation_verifier

# Start the verifier
python -m donation_verifier.main
```

## Running Services

You'll need multiple terminal windows/tabs to run all services simultaneously:

**Terminal 1 - Web Backend:**
```bash
cd fundlink_web
source ../.venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

**Terminal 2 - Telegram Bot:**
```bash
cd telbot_llm
source ../.venv/bin/activate
python run_bot.py
```

**Terminal 3 - Donation Verifier:**
```bash
cd donation_verifier
source ../.venv/bin/activate
python -m donation_verifier.main
```

### Access Points

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/
- **Django Admin**: http://localhost:8000/admin/ (requires superuser)

## Service Details

### Web Backend (Django)
- **Location**: `fundlink_web/`
- **Port**: 8000
- **Purpose**: REST API, admin interface, campaign management
- **Database**: SQLite by default (`fundlink_web/db.sqlite3`)
- **Commands**:
  ```bash
  python manage.py migrate          # Run migrations
  python manage.py createsuperuser  # Create admin user
  python manage.py collectstatic    # Collect static files
  python manage.py shell           # Django shell
  ```

### Telegram Bot
- **Location**: `telbot_llm/`
- **Purpose**: User interaction, donation deep links, LLM integration
- **Requires**: Valid `TELEGRAM_BOT_TOKEN`
- **Config**: Reads from root `.env` file
- **Features**: Dual-agent architecture with LLM support

### Donation Verifier
- **Location**: `donation_verifier/`
- **Purpose**: Monitor Avalanche blockchain for donations
- **Requires**: `INTERNAL_API_KEY` for backend communication
- **Chain**: Avalanche Fuji testnet
- **Config**: Auto-loads from root `.env`

## Development Workflow

### Starting Development
```bash
# Activate virtual environment
source .venv/bin/activate

# Quick start web backend only
cd fundlink_web
python manage.py runserver

# Or start all services (use multiple terminals)
# Terminal 1: Web backend
cd fundlink_web && python manage.py runserver

# Terminal 2: Bot (optional)
cd telbot_llm && python run_bot.py  

# Terminal 3: Verifier (optional)
cd donation_verifier && python -m donation_verifier.main
```

### Viewing Logs
- **Django**: Logs appear in the runserver terminal
- **Bot**: Logs appear in the bot terminal  
- **Verifier**: Logs appear in the verifier terminal
- **Log Level**: Controlled by `LOG_LEVEL` in `.env`

### Database Management
```bash
cd fundlink_web

# View database (SQLite)
sqlite3 db.sqlite3

# Django management
python manage.py migrate
python manage.py createsuperuser
python manage.py shell
python manage.py collectstatic
```

## Configuration Details

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `your-super-secret-key` |
| `INTERNAL_API_KEY` | Internal service authentication | `secure-api-key-123` |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | None |
| `TOGETHER_API_KEY` | Together AI API key for LLM features | None |
| `DEBUG` | Django debug mode | `true` |
| `LOG_LEVEL` | Application log level | `INFO` |

### Blockchain Configuration

The application is pre-configured for Avalanche Fuji testnet:
- **RPC URL**: https://api.avax-test.network/ext/bc/C/rpc  
- **Chain ID**: 43113
- **USDT Contract**: 0x5425890298aed601595a70AB815c96711a31Bc65

## Troubleshooting

## Troubleshooting

### Bot Service Not Starting
**Symptom**: Bot fails to start with token error
**Cause**: Invalid or missing `TELEGRAM_BOT_TOKEN`
**Solution**: 
1. Get a bot token from @BotFather on Telegram
2. Update `TELEGRAM_BOT_TOKEN` in `.env`
3. Restart bot: `cd telbot_llm && python run_bot.py`

### Verifier Service Not Starting  
**Symptom**: Verifier fails with "INTERNAL_API_KEY must be configured"
**Cause**: Missing `INTERNAL_API_KEY`
**Solution**: Ensure `INTERNAL_API_KEY` is set in `.env`

### Web Service Not Accessible
**Symptom**: Cannot access http://localhost:8000
**Solutions**:
1. Check if Django server is running in terminal
2. Verify no other service is using port 8000
3. Check for Django errors in terminal output
4. Ensure virtual environment is activated

### Database Errors
**Symptom**: Database connection or migration errors
**Solutions**:
1. Run migrations: `python manage.py migrate`
2. Check database file exists: `ls -la fundlink_web/db.sqlite3`
3. For PostgreSQL: Ensure PostgreSQL is running and credentials are correct

### Import Errors
**Symptom**: ModuleNotFoundError when starting services
**Solutions**:
1. Ensure virtual environment is activated: `source .venv/bin/activate`
2. Install dependencies: `pip install -r requirements-all.txt`
3. Check you're in the correct directory for each service

### Port Already in Use
**Symptom**: "Address already in use" error
**Solutions**:
1. Find process using port: `lsof -i :8000`
2. Kill process: `kill -9 <PID>`
3. Or use different port: `python manage.py runserver 8001`

## Development Tips

## Development Tips

### Process Management
Use a process manager like `tmux` or multiple terminal tabs:

```bash
# Using tmux (recommended)
tmux new-session -d -s fundlink

# Window 0: Web backend
tmux send-keys -t fundlink:0 'cd fundlink_web && source ../.venv/bin/activate && python manage.py runserver' Enter

# Window 1: Bot
tmux new-window -t fundlink
tmux send-keys -t fundlink:1 'cd telbot_llm && source ../.venv/bin/activate && python run_bot.py' Enter

# Window 2: Verifier  
tmux new-window -t fundlink
tmux send-keys -t fundlink:2 'cd donation_verifier && source ../.venv/bin/activate && python -m donation_verifier.main' Enter

# Attach to session
tmux attach -t fundlink
```

### Hot Reload
- **Django**: Automatically reloads on file changes (development server)
- **Bot**: Requires manual restart after code changes
- **Verifier**: Requires manual restart after code changes

### Testing Telegram Bot Locally
1. Install ngrok: https://ngrok.com/
2. Expose local port: `ngrok http 8000`
3. Update `TELEGRAM_WEBHOOK_URL` in `.env` with ngrok URL
4. Restart bot service

### Database Reset
```bash
cd fundlink_web

# SQLite: Delete and recreate
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser

# PostgreSQL: Drop and recreate database
dropdb fundlink && createdb fundlink
python manage.py migrate
```

### Environment Switching
```bash
# Different environments for different features
cp .env .env.backup
cp .env.development .env  # If you have different env files
```

### Development vs Production
- **Development**: Uses SQLite, DEBUG=true, simple logging
- **Production**: Uses PostgreSQL, DEBUG=false, structured logging
- **Testing**: Can use in-memory SQLite for faster tests

## API Endpoints

### Public Endpoints
- `GET /api/campaigns/` - List published campaigns
- `GET /api/campaigns/{id}/` - Campaign details
- `GET /api/ngos/` - List approved NGOs

### Bot Endpoints (Require `INTERNAL_API_KEY`)
- `GET /api/bot/campaigns/` - Campaigns for bot
- `POST /api/bot/notify/` - Donation notifications

### Admin Endpoints (Django Admin)
- `/admin/` - Full admin interface
- `/api/admin/` - Admin API endpoints

## Production Deployment

For production deployment, see:
- `DEPLOYMENT.md` - Production deployment guide  
- `docker-compose.prod.yml` - Docker production configuration (if using Docker)
- `railway-services.yml` - Railway deployment config

## Support

For issues and questions:
1. Check the terminal output for error messages
2. Ensure virtual environment is activated and dependencies installed
3. Review this guide and environment variables  
4. Check the main README.md for additional context
5. Open an issue on the GitHub repository

## Quick Reference

### Essential Commands
```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-all.txt
cp .env.example .env

# Web Backend
cd fundlink_web
python manage.py migrate && python manage.py runserver

# Bot (separate terminal)
cd telbot_llm && python run_bot.py

# Verifier (separate terminal)  
cd donation_verifier && python -m donation_verifier.main

# Database management
python manage.py migrate
python manage.py createsuperuser
python manage.py shell
```

### File Structure
```
fundlink/
├── .env                    # Main configuration
├── requirements-all.txt    # All dependencies
├── fundlink_web/          # Django backend
│   ├── manage.py
│   └── db.sqlite3         # Database file
├── telbot_llm/            # Telegram bot
│   └── run_bot.py
└── donation_verifier/     # Blockchain verifier
    └── main.py
```