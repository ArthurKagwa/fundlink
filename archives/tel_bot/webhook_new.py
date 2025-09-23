"""
Webhook server for Fundlink Telegram Bot.
Uses the modular architecture.
"""
import os
import logging
from flask import Flask, request
from dotenv import load_dotenv
from main import FundlinkBot
from config import WEBHOOK_HOST, WEBHOOK_PORT, WEBHOOK_URL

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app for webhook
app = Flask(__name__)

# Initialize bot
bot = None

def initialize_bot():
    """Initialize the bot instance."""
    global bot
    if not bot:
        bot = FundlinkBot()
        logger.info("Bot initialized for webhook mode")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook updates."""
    try:
        if not bot:
            initialize_bot()
        
        # Process the update
        update = request.get_json()
        # Note: In production, you'd need to properly handle the webhook update
        # For now, this is a basic structure
        
        logger.info(f"Received webhook update: {update}")
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "fundlink-bot"}, 200

def run_webhook_server():
    """Run the webhook server."""
    initialize_bot()
    
    logger.info(f"Starting webhook server on {WEBHOOK_HOST}:{WEBHOOK_PORT}")
    app.run(
        host=WEBHOOK_HOST,
        port=WEBHOOK_PORT,
        debug=False
    )

if __name__ == '__main__':
    run_webhook_server()