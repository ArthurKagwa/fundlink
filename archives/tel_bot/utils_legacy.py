"""
Legacy utilities for backward compatibility.
The actual functionality has been moved to the services/ directory.
"""
import logging

# Re-export from the new modular structure for backward compatibility
from services.api_client import APIClient
from services.deep_link import DeepLinkService as MetaMaskDeepLink
from services.message_formatter import MessageFormatter
from core.validators import validate_amount

logger = logging.getLogger(__name__)

def truncate_text(text: str, max_length: int = 4096) -> str:
    """Truncate text to fit Telegram message limits."""
    return MessageFormatter.truncate_text(text, max_length)

# Log that legacy imports are being used
logger.warning("Using legacy utils.py imports. Consider updating to use services/ directly.")