"""
Base handler class for Fundlink Telegram Bot handlers.
"""
import logging
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from telegram import Update
    from telegram.ext import ContextTypes
except ImportError:
    # Mock classes for testing without telegram installed
    Update = object
    ContextTypes = type('ContextTypes', (), {'DEFAULT_TYPE': object})

logger = logging.getLogger(__name__)


class BaseHandler:
    """Base class for all bot handlers."""
    
    def __init__(self, api_client, message_formatter):
        """Initialize handler with required services."""
        self.api_client = api_client
        self.message_formatter = message_formatter
        self.logger = logger
    
    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          error_message: str = "Something went wrong. Please try again.") -> None:
        """Handle errors gracefully."""
        self.logger.error(f"Handler error: {error_message}")
        
        if update.message:
            await update.message.reply_text(error_message)
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_message)
    
    async def log_user_action(self, user_id: int, action: str, data: Dict[str, Any] = None):
        """Log user actions for debugging and analytics."""
        log_data = {
            'user_id': user_id,
            'action': action,
            'data': data or {}
        }
        self.logger.info(f"User action: {log_data}")