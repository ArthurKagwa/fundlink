#!/usr/bin/env python
import os
import sys

# Add the project root to path to make imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up environment from .env if available
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Import and run the bot
from bot.main import run_polling

if __name__ == "__main__":
    print("Starting Telegram bot in polling mode...")
    run_polling()