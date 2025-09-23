"""
Main bot application for Fundlink Telegram Bot.
Modular MVP implementation with clean separation of concerns.
"""
import logging
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler
    from telegram import Update
    TELEGRAM_AVAILABLE = True
except ImportError:
    # Mock classes for testing without telegram installed
    Application = None
    CommandHandler = None
    CallbackQueryHandler = None
    Update = None
    TELEGRAM_AVAILABLE = False
    logging.warning("python-telegram-bot not available")

# Import modular components
from config import BOT_TOKEN, DEBUG, LOG_LEVEL
from services import APIClient, MessageFormatter
from handlers import CommandHandlers, CallbackHandlers
from core.exceptions import ConfigurationError

# Configure logging
log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=log_level
)
logger = logging.getLogger(__name__)


class FundlinkBot:
    """Main bot application class."""
    
    def __init__(self):
        """Initialize the bot with all services and handlers."""
        self._validate_config()
        
        # Initialize services
        self.api_client = APIClient()
        self.message_formatter = MessageFormatter()
        
        # Initialize handlers
        self.command_handlers = CommandHandlers(self.api_client, self.message_formatter)
        self.callback_handlers = CallbackHandlers(self.api_client, self.message_formatter)
        
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()
        self._register_handlers()
        
        logger.info("Fundlink bot initialized successfully")
    
    def _validate_config(self):
        """Validate bot configuration."""
        if not BOT_TOKEN:
            raise ConfigurationError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        logger.info(f"Bot configuration validated (debug={'on' if DEBUG else 'off'})")
    
    def _register_handlers(self):
        """Register all command and callback handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.command_handlers.start))
        self.application.add_handler(CommandHandler("campaigns", self.command_handlers.campaigns))
        self.application.add_handler(CommandHandler("donate", self.command_handlers.campaigns))  # Alias
        self.application.add_handler(CommandHandler("history", self.command_handlers.history))
        self.application.add_handler(CommandHandler("help", self.command_handlers.help_command))
        
        # Callback query handlers
        self.application.add_handler(
            CallbackQueryHandler(self.callback_handlers.campaign_detail, pattern=r"^campaign_\d+$")
        )
        self.application.add_handler(
            CallbackQueryHandler(self.callback_handlers.handle_donation, pattern=r"^donate_\d+_\w+_[\d.]+$")
        )
        self.application.add_handler(
            CallbackQueryHandler(self.callback_handlers.back_to_campaigns, pattern="^back_campaigns$")
        )
        
        logger.info("All handlers registered successfully")
    
    def run_polling(self):
        """Run the bot using polling."""
        logger.info("Starting Fundlink bot with polling...")
        try:
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            raise
    
    def run_webhook(self, webhook_url: str, port: int = 8443, host: str = '0.0.0.0'):
        """Run the bot using webhooks."""
        logger.info(f"Starting Fundlink bot with webhook: {webhook_url}")
        try:
            self.application.run_webhook(
                listen=host,
                port=port,
                webhook_url=webhook_url,
                allowed_updates=Update.ALL_TYPES
            )
        except Exception as e:
            logger.error(f"Webhook bot crashed: {e}")
            raise


def main():
    """Main entry point for the bot."""
    try:
        bot = FundlinkBot()
        bot.run_polling()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())