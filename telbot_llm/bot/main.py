import os
import logging
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
from .handlers.chat import start, chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def build():
    """Build and configure the application with handlers"""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    return app

def run_polling(drop_pending=False):
    """Run bot in polling mode"""
    app = build()
    logger.info("Starting bot in polling mode")
    app.run_polling(drop_pending_updates=drop_pending)

def run_webhook(webhook_url, listen="0.0.0.0", port=8443, secret_token=None):
    """Run bot in webhook mode"""
    app = build()
    
    # Extract the path component from the webhook URL
    from urllib.parse import urlparse
    url_parts = urlparse(webhook_url)
    path = url_parts.path
    
    logger.info(f"Starting bot in webhook mode with path: {path}")
    
    app.run_webhook(
        listen=listen,
        port=port,
        url_path=path,
        webhook_url=webhook_url,
        secret_token=secret_token,
    )

if __name__ == "__main__":
    # Default to polling when run directly
    run_polling()