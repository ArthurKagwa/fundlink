import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application
import asyncio
import json
from bot import FundlinkBot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', '')

# Initialize Flask app for webhook
app = Flask(__name__)

# Initialize bot application
application = None
bot_instance = None

def setup_bot():
    """Initialize the bot application and handlers."""
    global application, bot_instance
    
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return False
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Create bot instance
    bot_instance = FundlinkBot()
    
    # Register handlers
    from telegram.ext import CommandHandler, CallbackQueryHandler
    application.add_handler(CommandHandler("start", bot_instance.start))
    application.add_handler(CommandHandler("campaigns", bot_instance.campaigns))
    application.add_handler(CommandHandler("donate", bot_instance.campaigns))
    application.add_handler(CommandHandler("history", bot_instance.history))
    application.add_handler(CommandHandler("help", bot_instance.help_command))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(bot_instance.campaign_detail, pattern=r"^campaign_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_donation, pattern=r"^donate_\d+_\w+_[\d.]+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.back_to_campaigns, pattern="^back_campaigns$"))
    
    logger.info("Bot handlers registered successfully")
    return True

@app.route('/webhook/telegram', methods=['POST'])
def webhook():
    """Handle incoming webhook updates from Telegram."""
    if not application:
        logger.error("Bot application not initialized")
        return 'Bot not ready', 500
    
    try:
        # Parse the update
        update_data = request.get_json(force=True)
        update = Update.de_json(update_data, application.bot)
        
        # Process the update
        asyncio.run(application.process_update(update))
        
        return 'OK', 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return 'Error', 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'bot_initialized': application is not None
    }

@app.route('/webhook/set', methods=['POST'])
def set_webhook():
    """Set the webhook URL for the bot."""
    if not application or not WEBHOOK_URL:
        return {'error': 'Bot or webhook URL not configured'}, 400
    
    try:
        # Set webhook
        success = asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL))
        
        if success:
            return {'message': 'Webhook set successfully', 'url': WEBHOOK_URL}
        else:
            return {'error': 'Failed to set webhook'}, 500
            
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return {'error': str(e)}, 500

@app.route('/webhook/info', methods=['GET'])
def webhook_info():
    """Get current webhook information."""
    if not application:
        return {'error': 'Bot not initialized'}, 400
    
    try:
        webhook_info = asyncio.run(application.bot.get_webhook_info())
        return {
            'url': webhook_info.url,
            'has_custom_certificate': webhook_info.has_custom_certificate,
            'pending_update_count': webhook_info.pending_update_count,
            'last_error_date': webhook_info.last_error_date,
            'last_error_message': webhook_info.last_error_message,
            'max_connections': webhook_info.max_connections,
            'allowed_updates': webhook_info.allowed_updates
        }
        
    except Exception as e:
        logger.error(f"Error getting webhook info: {e}")
        return {'error': str(e)}, 500

def create_app():
    """Application factory."""
    if setup_bot():
        logger.info("Fundlink bot webhook server initialized successfully")
    else:
        logger.error("Failed to initialize bot")
    
    return app

if __name__ == '__main__':
    # Development mode - run with polling instead of webhook
    if os.getenv('BOT_DEBUG', 'false').lower() == 'true':
        logger.info("Running in development mode with polling")
        from bot import main
        main()
    else:
        # Production mode - run Flask webhook server
        app = create_app()
        port = int(os.getenv('WEBHOOK_PORT', 8443))
        host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
        
        logger.info(f"Starting webhook server on {host}:{port}")
        app.run(host=host, port=port, debug=False)