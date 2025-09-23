"""
Custom exceptions for Fundlink Telegram Bot.
"""


class FundlinkBotError(Exception):
    """Base exception for Fundlink bot errors."""
    pass


class APIError(FundlinkBotError):
    """Raised when API communication fails."""
    
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class ValidationError(FundlinkBotError):
    """Raised when input validation fails."""
    pass


class ConfigurationError(FundlinkBotError):
    """Raised when bot configuration is invalid."""
    pass


class DeepLinkError(FundlinkBotError):
    """Raised when deep link generation fails."""
    pass