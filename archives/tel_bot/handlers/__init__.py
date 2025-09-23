"""
Handlers package for Fundlink Telegram Bot.
Contains all command and callback query handlers.
"""

# Import order matters for avoiding circular imports
try:
    from .base import BaseHandler
    from .commands import CommandHandlers
    from .callbacks import CallbackHandlers
    
    __all__ = ['BaseHandler', 'CommandHandlers', 'CallbackHandlers']
except ImportError as e:
    # Graceful fallback for development
    import logging
    logging.warning(f"Handler import error: {e}. Some modules may not be available.")
    __all__ = []