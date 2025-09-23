"""
Fundlink Telegram Bot - Entry Point
Modular MVP implementation for humanitarian donations on Avalanche Fuji testnet.

This is the main entry point that maintains backward compatibility
while using the new modular architecture.
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import and run the modular bot
from main import main

if __name__ == '__main__':
    main()