"""
Services package for Fundlink Telegram Bot.
Contains business logic and external API integrations.
"""

try:
    from .deep_link import DeepLinkService
    from .message_formatter import MessageFormatter
    from .api_client import APIClient
    
    __all__ = ['APIClient', 'DeepLinkService', 'MessageFormatter']
except ImportError as e:
    # Graceful fallback for development
    import logging
    logging.warning(f"Service import error: {e}. Some modules may not be available.")
    __all__ = []