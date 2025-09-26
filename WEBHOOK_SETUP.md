# Telegram Webhook Setup for Deployment

## Overview

The FundLink Telegram bot supports both polling (development) and webhook (production) modes. For production deployment, webhooks are recommended for better performance and reliability.

## Webhook URL Structure

The webhook endpoint is: `/bot/api/webhook/telegram/`

Your webhook URL will be: `https://your-deployed-domain.com/bot/api/webhook/telegram/`

## Platform-Specific Setup

### 1. Render Deployment

When deploying to Render:

1. **Get your service URL** from Render dashboard (e.g., `https://fundlink-web-abc123.onrender.com`)

2. **Update environment variables**:
   ```bash
   TELEGRAM_WEBHOOK_URL=https://fundlink-web-abc123.onrender.com/bot/api/webhook/telegram/
   PUBLIC_WEBHOOK_BASE=https://fundlink-web-abc123.onrender.com
   ```

3. **Deploy with webhook mode**:
   - The `render.yaml` automatically configures webhook mode
   - Render will set the webhook URL when the service starts

### 2. Railway Deployment

When deploying to Railway:

1. **Get your Railway URL** (e.g., `https://fundlink-production.up.railway.app`)

2. **Set environment variables**:
   ```bash
   TELEGRAM_WEBHOOK_URL=https://fundlink-production.up.railway.app/bot/api/webhook/telegram/
   PUBLIC_WEBHOOK_BASE=https://fundlink-production.up.railway.app
   ```

### 3. VPS/Docker Deployment

For VPS with custom domain:

1. **Configure your domain** (e.g., `https://fundlink.yourdomain.com`)

2. **Update docker-compose.prod.yml environment**:
   ```yaml
   environment:
     TELEGRAM_WEBHOOK_URL: https://fundlink.yourdomain.com/bot/api/webhook/telegram/
     PUBLIC_WEBHOOK_BASE: https://fundlink.yourdomain.com
   ```

3. **Ensure SSL/HTTPS** - Telegram requires HTTPS for webhooks

## Setting the Webhook

### Method 1: Automatic (Recommended)

The bot automatically sets the webhook when started in webhook mode. Just ensure your environment variables are correct.

### Method 2: Manual Webhook Setup

If you need to manually set the webhook:

```bash
# Replace with your bot token and webhook URL
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://your-deployed-domain.com/bot/api/webhook/telegram/",
       "secret_token": "your-webhook-secret"
     }'
```

### Method 3: Using the Bot Management Command

From the Django management commands:

```bash
# In your deployed environment
python manage.py set_telegram_webhook --url https://your-domain.com/bot/api/webhook/telegram/
```

## Environment Variables for Production

### Required Variables:
```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_WEBHOOK_URL=https://your-domain.com/bot/api/webhook/telegram/
PUBLIC_WEBHOOK_BASE=https://your-domain.com
TELEGRAM_WEBHOOK_SECRET=optional-webhook-secret-for-security

# Internal API
INTERNAL_API_KEY=your-secure-api-key

# Django
SECRET_KEY=your-django-secret-key
DEBUG=false
ALLOWED_HOSTS=your-domain.com,*.your-domain.com
```

## Webhook Security

### 1. Secret Token (Recommended)

Set a webhook secret for additional security:

```bash
TELEGRAM_WEBHOOK_SECRET=your-random-secret-string
```

### 2. IP Whitelist

Telegram webhook IPs (optional firewall configuration):
- `149.154.160.0/20`
- `91.108.4.0/22`

## Testing Webhook Setup

### 1. Check Webhook Status

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

Should return:
```json
{
  "ok": true,
  "result": {
    "url": "https://your-domain.com/bot/api/webhook/telegram/",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "last_error_date": 0,
    "max_connections": 40,
    "allowed_updates": ["message", "callback_query"]
  }
}
```

### 2. Test Bot Response

Send a message to your bot on Telegram. Check your application logs for:
```
INFO:telegram.ext.Application:Received webhook update
```

## Troubleshooting

### Webhook Not Receiving Updates

1. **Check webhook URL is accessible**:
   ```bash
   curl -X POST https://your-domain.com/bot/api/webhook/telegram/
   ```

2. **Verify SSL certificate** - Telegram requires valid HTTPS

3. **Check webhook info** for error messages

4. **Ensure correct environment variables** are set

### Bot Not Responding

1. **Check application logs** for errors
2. **Verify INTERNAL_API_KEY** is correctly set
3. **Check database connectivity**
4. **Ensure all required services are running**

## Switching Between Polling and Webhook

### Development (Polling):
```bash
# Run locally with polling
cd telbot_llm
python run_bot.py
```

### Production (Webhook):
```bash
# Webhook mode is automatically used when TELEGRAM_WEBHOOK_URL is set
# and the application is run with webhook configuration
```

## Example: Complete Deployment Flow

1. **Deploy your application** to chosen platform
2. **Get your deployment URL** (e.g., `https://fundlink-abc123.onrender.com`)
3. **Update environment variables**:
   ```bash
   TELEGRAM_WEBHOOK_URL=https://fundlink-abc123.onrender.com/bot/api/webhook/telegram/
   PUBLIC_WEBHOOK_BASE=https://fundlink-abc123.onrender.com
   ```
4. **Restart your service** - webhook is automatically set
5. **Test bot** by sending a message on Telegram
6. **Check logs** to confirm webhook reception
7. **Verify webhook status** using getWebhookInfo API

## Notes

- **Development**: Use ngrok + polling mode
- **Production**: Use proper domain + webhook mode  
- **HTTPS Required**: Telegram webhooks require SSL
- **Path Important**: Must match `/bot/api/webhook/telegram/`
- **Secret Token**: Optional but recommended for security