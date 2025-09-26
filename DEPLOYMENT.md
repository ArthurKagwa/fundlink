# FundLink Deployment Guide

This guide covers deploying the complete FundLink stack including:
- **Web App**: Django backend with DRF API
- **Telegram Bot**: LLM-powered donation assistant  
- **Verifier**: On-chain donation verification service

## Deployment Options

### 1. Docker Compose (Recommended for Local/VPS)

For local development or VPS deployment:

```bash
# Development
docker-compose up -d

# Production  
docker-compose -f docker-compose.prod.yml up -d
```

**Environment Setup:**
1. Copy `.env.example` to `.env`
2. Fill in required values:
   - `SECRET_KEY` (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `TELEGRAM_BOT_TOKEN`
   - `TOGETHER_API_KEY` (for LLM)
   - `POSTGRES_PASSWORD`

### 2. Render (Easiest Cloud Deployment)

1. **Connect Repository**: Link your GitHub repo to Render
2. **Deploy from Blueprint**: Use `render.yaml` for automated setup
3. **Configure Environment Variables**:
   - `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
   - `TOGETHER_API_KEY`: API key from Together.ai
   - `TELEGRAM_WEBHOOK_URL`: Your web service URL + `/api/bot/webhook/`

**Manual Setup:**
- Create PostgreSQL database
- Deploy web service (auto-migrates and serves static files)
- Deploy bot worker (connects to web service)
- Deploy verifier worker (monitors blockchain)

### 3. Railway

1. **Deploy Web Service**:
   ```bash
   railway login
   railway new fundlink-web
   railway add postgresql
   railway up
   ```

2. **Deploy Bot Service**:
   ```bash
   railway new fundlink-bot
   railway up
   ```

3. **Deploy Verifier**:
   ```bash
   railway new fundlink-verifier  
   railway up
   ```

**Link Services**: Share `INTERNAL_API_KEY` across all services.

### 4. Fly.io

Create three applications:

```bash
# Web app
flyctl apps create fundlink-web
flyctl postgres create --name fundlink-db
flyctl deploy --app fundlink-web

# Bot
flyctl apps create fundlink-bot
flyctl deploy --app fundlink-bot

# Verifier
flyctl apps create fundlink-verifier
flyctl deploy --app fundlink-verifier
```

## Required Environment Variables

### Core Variables (All Services)
```env
SECRET_KEY=your-secret-key
INTERNAL_API_KEY=shared-service-key
DEBUG=false
```

### Web Service
```env
ALLOWED_HOSTS=your-domain.com
DB_ENGINE=django.db.backends.postgresql
DB_NAME=fundlink
DB_USER=fundlink
DB_PASSWORD=secure-password
DB_HOST=database-host
DB_PORT=5432
```

### Telegram Bot
```env
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/api/bot/webhook/
TOGETHER_API_KEY=your-llm-api-key
TOGETHER_MODEL=meta-llama/Llama-3.2-3B-Instruct-Turbo
BACKEND_URL=https://your-web-service-url
```

### Donation Verifier
```env
AVALANCHE_RPC_URL=https://api.avax-test.network/ext/bc/C/rpc
AVALANCHE_CHAIN_ID=43113
USDT_CONTRACT_ADDRESS=0x5425890298aed601595a70AB815c96711a31Bc65
VERIFICATION_INTERVAL=30
BACKEND_URL=https://your-web-service-url
```

## Post-Deployment Steps

### 1. Database Setup
```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load initial data (optional)
python manage.py loaddata initial_data.json
```

### 2. Telegram Bot Setup
1. Create bot with @BotFather
2. Set webhook URL: `https://your-domain.com/api/bot/webhook/`
3. Test bot with `/start` command

### 3. Verify Services
- **Web**: Visit `/admin/` and `/api/campaigns/`
- **Bot**: Send `/campaigns` to your bot
- **Verifier**: Check logs for blockchain connection

## Monitoring & Maintenance

### Health Checks
- **Web**: `GET /health/` returns service status
- **Bot**: Monitor Telegram webhook delivery
- **Verifier**: Check donation processing logs

### Scaling Considerations
- **Web**: Horizontal scaling with load balancer
- **Bot**: Single instance (webhook limitations)
- **Verifier**: Single instance (state management)

### Database Maintenance
```bash
# Backup
pg_dump fundlink > backup.sql

# Monitor performance
SELECT * FROM pg_stat_activity;
```

## Security Checklist

- [ ] `DEBUG=false` in production
- [ ] Strong `SECRET_KEY` and `INTERNAL_API_KEY`
- [ ] HTTPS enabled for all services
- [ ] Database connections encrypted
- [ ] Environment variables secured
- [ ] Regular security updates

## Troubleshooting

### Common Issues

**Bot not responding:**
- Verify `TELEGRAM_BOT_TOKEN` 
- Check webhook URL accessibility
- Review bot service logs

**Donations not confirming:**
- Test Avalanche RPC connection
- Verify contract addresses
- Check verifier service logs

**Database connection errors:**
- Confirm database credentials
- Test network connectivity
- Check connection pooling

### Logs and Debugging

```bash
# Docker Compose
docker-compose logs web
docker-compose logs bot
docker-compose logs verifier

# Railway
railway logs --service web
railway logs --service bot

# Render
# Check service logs in dashboard
```

## Cost Estimates

### Render (Monthly)
- Web service: $7/month (Starter)
- Bot worker: $7/month  
- Verifier worker: $7/month
- PostgreSQL: $7/month
- **Total: ~$28/month**

### Railway (Monthly)
- 3 services: $15-30/month
- PostgreSQL: $5-10/month  
- **Total: ~$20-40/month**

### VPS + Docker
- VPS (2GB RAM): $10-20/month
- Self-managed PostgreSQL
- **Total: ~$10-20/month**

---

Choose the deployment method that best fits your technical expertise and budget. Render is recommended for beginners, while Docker Compose on VPS offers the most control and cost efficiency.