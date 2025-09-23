# Fundlink Telegram Bot

A Telegram bot for the Fundlink humanitarian donations platform on Avalanche Fuji testnet.

## Features

- 🤖 **Conversational Interface**: Easy-to-use Telegram bot with inline keyboards
- 💰 **Multi-Token Support**: Donate AVAX or USDT to verified NGOs
- 🦊 **MetaMask Integration**: Generate deep links for seamless wallet integration
- 📊 **Donation Tracking**: View donation history and transaction confirmations
- 🎯 **Campaign Browse**: Discover and support active humanitarian campaigns
- ✅ **Real-time Notifications**: Get notified when donations are confirmed on-chain

## Setup

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Access to Fundlink Django backend API

### Installation

1. **Clone and navigate to bot directory:**
   ```bash
   cd tel_bot
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start the bot:**
   ```bash
   ./start.sh
   ```

## Configuration

Edit the `.env` file with your settings:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
BACKEND_URL=https://your-backend-url.com

# Optional
INTERNAL_API_KEY=your_internal_service_key
BOT_DEBUG=true  # Use polling instead of webhooks
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram
```

## Bot Commands

- `/start` - Welcome message and bot introduction
- `/campaigns` - Browse active donation campaigns  
- `/donate` - Alias for /campaigns command
- `/history` - View your donation history
- `/help` - Show help information

## Architecture

### Development Mode (Polling)
Set `BOT_DEBUG=true` in `.env` to run with polling for development:
```bash
python bot.py
```

### Production Mode (Webhooks)
Set `BOT_DEBUG=false` and configure webhook URL:
```bash
python webhook.py
```

The webhook server runs on Flask and handles incoming updates from Telegram.

## API Integration

The bot integrates with the Fundlink Django backend through REST API endpoints:

- `GET /api/campaigns/` - Fetch active campaigns
- `GET /api/campaigns/{id}/` - Get campaign details  
- `GET /api/donations/?telegram_id=X` - User donation history
- `POST /api/bot/register-user/` - Register/update bot users
- `POST /api/donations/pending/` - Track pending donations
- `POST /api/bot/notify/` - Receive donation confirmations

## Donation Flow

1. User browses campaigns with `/campaigns`
2. Selects campaign and donation amount
3. Bot generates MetaMask deep link with recipient address and amount
4. User clicks link, MetaMask opens with pre-filled transaction
5. User confirms transaction in MetaMask
6. Donation verifier detects on-chain transaction
7. Backend calls bot notification endpoint
8. Bot sends confirmation receipt to user

## MetaMask Deep Links

The bot generates platform-specific deep links:

**AVAX (native token):**
```
https://metamask.app.link/send/0xRecipientAddress?value=AmountInWei
```

**USDT (ERC-20 token):**
```
https://metamask.app.link/send/0xRecipientAddress?value=AmountInUnits&contractAddress=0xUSDTContract
```

## File Structure

```
tel_bot/
├── bot.py              # Main bot logic with polling
├── webhook.py          # Flask webhook server  
├── config.py           # Configuration and constants
├── utils.py            # API client and utilities
├── requirements.txt    # Python dependencies
├── start.sh           # Startup script
├── .env.example       # Environment template
└── README.md          # This file
```

## Development

### Running Tests
```bash
# TODO: Add test suite
python -m pytest tests/
```

### Adding New Features

1. **New Commands**: Add handlers in `bot.py` and register in setup functions
2. **New API Endpoints**: Update `utils.py` APIClient class
3. **Message Templates**: Add to `config.py` MESSAGES dict
4. **Webhook Endpoints**: Add routes in `webhook.py`

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check webhook status:
```bash
curl https://your-domain.com/webhook/info
```

## Deployment

### Railway/Render/Fly.io

1. Set environment variables in platform dashboard
2. Use `webhook.py` as entry point
3. Set webhook URL in Telegram: `POST /webhook/set`

### Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "webhook.py"]
```

## Security

- ✅ HMAC signature verification for backend callbacks
- ✅ Environment variable for sensitive tokens
- ✅ Input validation for user data
- ✅ Rate limiting considerations
- ✅ Error handling and logging

## Troubleshooting

### Common Issues

**Bot not responding:**
- Check bot token is valid
- Verify backend URL is accessible
- Check logs for error messages

**Webhook not receiving updates:**
- Verify webhook URL is publicly accessible
- Check webhook is set: `GET /webhook/info`
- Ensure SSL certificate is valid

**MetaMask links not working:**
- Verify wallet addresses are checksummed
- Check amount calculations for wei/decimals
- Test links in mobile browser first

## Support

For issues and questions:
1. Check the logs for error messages
2. Verify all environment variables are set
3. Test API endpoints manually
4. Check Telegram Bot API status

## License

Part of the Fundlink humanitarian donations platform.